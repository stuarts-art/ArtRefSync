from asyncio import Event
from collections import defaultdict
from enum import StrEnum, auto
import json
from queue import Empty, Queue
import os
import shutil
import sqlite3
from typing import Iterable
import jsonpickle
from pathlib import Path
import requests
from artrefsync.db.dataclass_db import Dataclass_DB
from artrefsync.db.post_db import PostDb
from artrefsync.stats import stats
from artrefsync.stores.link_cache import Link_Cache
from artrefsync.stores.storage import ImageStoreHandler
from artrefsync.constants import APP, BOARD, LOCAL, STATS, STORE, TABLE
from artrefsync.boards.board_handler import Post, PostFile
from artrefsync.config import config

import logging

from artrefsync.utils.PyInstallerUtils import resource_path

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)

class DIRS(StrEnum):
    FILE = auto()
    PREVIEW = ".previews"
    SAMPLE = ".sample"

def main():
    config[TABLE.LOCAL][LOCAL.ARTIST_DIR]= "artists"
    plain_storage = PlainLocalStorage()


class PlainLocalStorage(ImageStoreHandler):
    def __init__(self):
        self.artists_base_dir = resource_path(Path(config[TABLE.LOCAL][LOCAL.ARTIST_DIR]))
        self.dir_base_map = {}
        self.dir_map: dict[DIRS, dict[BOARD, dict[str, str]]]= defaultdict(dict)
        self.update_map: dict = {}
        self.file_map: dict = defaultdict(dict)
        self.dir_base_map[DIRS.FILE] = resource_path(Path(config[TABLE.LOCAL][LOCAL.ARTIST_DIR]))
        self.dir_base_map[DIRS.PREVIEW] = os.path.join(self.dir_base_map[DIRS.FILE], DIRS.PREVIEW)
        self.dir_base_map[DIRS.SAMPLE] = os.path.join(self.dir_base_map[DIRS.FILE], DIRS.SAMPLE)

        prev = 0
        loaded = 0

        for dir in DIRS:
            base_path = self.dir_base_map[dir]
            # print(base_path)
            os.makedirs(base_path, exist_ok=True)
            for board in BOARD:
                board_path = Path(os.path.join(base_path, board.value))
                os.makedirs(board_path, exist_ok=True)
                self.dir_map[dir][board] = {}
                self.dir_map[dir][board][board] = board_path

                for artist_path in board_path.iterdir():
                    update_time = os.path.getmtime(artist_path)
                    artist = artist_path.name
                    self.dir_map[dir][board][artist] = artist_path
                    self.update_map[dir] = update_time
                    for file in artist_path.iterdir():
                        pid = file.name.rsplit('.', maxsplit=1)[0].split('-')[0]
                        if not pid:
                            continue
                        self.file_map[artist_path][pid] = file
                        loaded += 1
                    # print(f"{artist} - {loaded - prev}")
                    prev = loaded
        
    def get_artist_posts(self, dir, board, artist) -> dict[str, str]:
        artist_dir = self.get_artist_dir(dir, board, artist)
        # print(artist_dir)
        update_time = os.path.getmtime(self.artists_base_dir)
        last_updated = self.update_map[artist_dir]  if artist_dir in self.update_map else None
        
        if artist_dir in self.update_map:
            if update_time == last_updated:
                return self.file_map[artist_dir]

        for file in Path.iterdir(artist_dir):
            pid = file.name.rsplit('.', maxsplit=1)[0].split('-')[0]
            if not pid:
                continue
            self.file_map[artist_dir][pid] = file
        self.update_map[artist_dir] = update_time
        return self.file_map[artist_dir]

    def get_artist_dir(self, dir:DIRS, board:BOARD, artist):
        if artist in self.dir_map[dir][board]:
            return self.dir_map[dir][board][artist]
        else:
            artist_dir = os.path.join(self.dir_map[dir][board][board], artist)
            os.makedirs(artist_dir, exist_ok=True)
            self.dir_map[dir][board][artist] = artist_dir
            return artist_dir
    
    def get_store(self) -> STORE:
        return STORE.LOCAL

    def get_board_artist_folder(self, board: BOARD, artist:str):
        artist_folder = os.path.join(self.artists_folder, board, artist)
        os.makedirs(artist_folder, exist_ok=True)
        return artist_folder  

    def create_board_and_artist_folders(self, board: BOARD, artists: Iterable[str]):
        logger.debug("Creating Board for %s, and artists: %s", board, artists)
        for artist in artists:
            for dir in DIRS:
                self.get_artist_dir(dir, board, artist)


    def get_posts(self, board: BOARD, artist: str):
        """
        Returns a partial PostFile Object. Remaining metadata should be added using a Post object.
        """
        files = self.get_artist_posts(DIRS.FILE, board, artist)
        previews = self.get_artist_posts(DIRS.PREVIEW, board, artist)
        samples = self.get_artist_posts(DIRS.SAMPLE, board, artist)
        post_files = {}

        for pid, file in files.items():
            preview = previews[pid] if pid in previews else ""
            sample = samples[pid] if pid in samples else ""
            post_file = PostFile(id=pid,
                ext_id= str(file),
                store=self.get_store(),
                board=board,
                artist_name=artist,
                file=str(file),
                preview=str(preview),
                sample=str(sample)
            )
            post_files[pid] = post_file
        return post_files

    def save_post(
        self, post: Post, link_cache: Link_Cache = None, event: Event = None
    ) -> Post | None:
        saved_posts = {}
        for dir in DIRS:
            saved_file = self.save_link(post, link_cache, dir)
            if saved_file:
                saved_posts[dir] = saved_file
        return saved_posts

    def save_link(self, post: Post, link_cache, dir = DIRS) -> bool:
        pid = post.id
        link = ""
        suffix = ""
        match(dir):
            case DIRS.FILE:
                link = post.file_link
            case DIRS.SAMPLE:
                link = post.sample_link
                suffix = "-sample"
            case DIRS.PREVIEW:
                link = post.preview_link
                suffix = "-preview"
        if not link:
            logger.debug("Skipping downloading %s for %s. No link.", dir.value, pid)
            return ""

        file_dir = self.get_artist_dir(dir= dir, board=post.board, artist=post.artist_name)
        link_ext = link.split('.')[-1]
        file_name = f"{pid}{suffix}.{link_ext}"
        file_path = os.path.join(file_dir, file_name)

        if os.path.exists(file_path):
            logger.debug("Skipping downloading %s for %s. Already exists.", dir.value, pid)
            return file_path

        try:
            temp_thumbnail = link_cache.get_file_from_link(link)
            shutil.copy2(temp_thumbnail, file_path)
        except:
            return ""
        return file_path

    get_thumbnail_order = [DIRS.PREVIEW, DIRS.SAMPLE, DIRS.FILE]
    def get_thumbnail(self, post):
        for dir in self.get_thumbnail_order:
            posts = self.get_artist_posts(dir, post.board, post.artist_name)
            if post.id in posts:
                return posts[post.id]
        return ""

    def update_post(self, board: BOARD, post: Post):
        logger.warning("Update post called for  %s but this method is not implemented yet.", post.id)
        # No Metadata is saved...right?
        pass


if __name__ == "__main__":
    main()

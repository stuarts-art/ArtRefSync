from asyncio import Event
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
from artrefsync.stats import stats
from artrefsync.stores.link_cache import Link_Cache
from artrefsync.stores.storage import ImageStorage
from artrefsync.constants import APP, BOARD, LOCAL, STATS, STORE, TABLE
from artrefsync.boards.board_handler import Post, PostFile
from artrefsync.config import config

import logging

from artrefsync.utils.PyInstallerUtils import resource_path

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


def main():
    config = {TABLE.LOCAL: {LOCAL.ARTIST_DIR: "artists"}}
    plain_storage = PlainLocalStorage()


class PlainLocalStorage(ImageStorage):
    def __init__(self):
        self.artists_folder = resource_path(Path(config[TABLE.LOCAL][LOCAL.ARTIST_DIR]))
        self.thumbnail_folder = os.path.join(self.artists_folder, "thumbnails")
        self.board_artist_posts = {}
        self.board_artist_paths = {}
        self.board_paths = {}
        self.post_write_queue: Queue[Post] = Queue()
        self.writing_event = Event()
        self.db_path = resource_path(
            os.path.join(config[TABLE.APP][APP.DB_DIR], "tagapp.local.db")
        )
        # self.db_name = "tagapp.local.db"
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        # if os.path.
        if not os.path.isdir(self.thumbnail_folder):
            os.mkdir(self.thumbnail_folder)

        if not os.path.exists(self.artists_folder):
            os.mkdir(self.artists_folder)
        for board in BOARD:
            self.board_artist_posts[board] = {}
            self.board_artist_paths[board] = {}
            board_path = Path(os.path.join(self.artists_folder, board.value))
            self.board_paths[board] = board_path
            if not os.path.exists(board_path):
                os.mkdir(board_path)
            # get artists from board_path
            for artist_path in Path.iterdir(board_path):
                artist_name = artist_path.name
                self.board_artist_posts[board][artist_name] = {}
                self.board_artist_paths[board][artist_name] = artist_path

                for post in Path.iterdir(board_path):
                    # if post.suffix == ".json":
                    pid = post.name.split("-", maxsplit=1)[0]
                    if pid:
                        self.board_artist_posts[board][artist_name][pid] = post

    def get_store(self) -> STORE:
        return STORE.LOCAL

    def create_board_and_artist_folders(self, board: str, artists: Iterable[str]):
        logger.debug("Creating Board for %s, and artists: %s", board, artists)
        board_folder = os.path.join(self.artists_folder, board)
        self.board_paths[board] = board_folder
        self.board_artist_posts[board] = {}
        self.board_artist_paths[board] = {}

        if not os.path.isdir(self.artists_folder):
            os.mkdir(board_folder)

        for artist in artists:
            artist_folder = os.path.join(board_folder, artist)
            if not os.path.isdir(artist_folder):
                logger.info("Creating folder %s", artist_folder)
                os.makedirs(artist_folder, exist_ok=True)
            self.board_artist_paths[board][artist] = artist_folder

        # return super().create_board_and_artist_folders(board, artists)

    def get_posts(self, board: BOARD, artist: str):
        logger.debug("GEtting posts for Board for %s, and artist: %s", board, artist)
        with Dataclass_DB(PostFile, db_name=self.db_path) as post_file_db:
            result = post_file_db.select(
                conditions=[("board", str(board)), ("artist_name", artist)]
            )
            if result:
                return {post.id: post for post in result}
        return {}

    def queue_db_write(self, post: Post):
        logger.debug("Writing to DB %post", post)
        self.post_write_queue.put(post)
        if self.writing_event.is_set():
            return
        self.writing_event.set()
        with Dataclass_DB(PostFile, db_name=self.db_path) as post_file_db:
            try:
                while not self.post_write_queue.empty():
                    qpost = self.post_write_queue.get_nowait()
                    postfile = PostFile(
                        id=qpost.id,
                        ext_id=qpost.ext_id,
                        store=self.get_store().value,
                        board=qpost.board,
                        artist_name=qpost.artist_name,
                        height=qpost.height,
                        width=qpost.width,
                        ratio=qpost.ratio,
                        ext=qpost.ext,
                        thumbnail=qpost.thumbnail,
                        file=qpost.file,
                    )
                    post_file_db.insert(postfile)
            except Empty:
                pass
        self.writing_event.clear()

    def save_post(
        self, post: Post, link_cache: Link_Cache = None, event: Event = None
    ) -> Post | None:
        logger.debug("Saving post :", post)
        board = str(post.board)
        artist = post.artist_name
        # board_path = self.board_paths[board]
        artist_path = self.board_artist_paths[BOARD(post.board)][artist]

        file_name = os.path.join(artist_path, f"{post.name}.{post.ext}")
        temp_file = link_cache.get_file_from_link(post.url)
        shutil.copy2(temp_file, file_name)
        post.file = file_name

        try:
            temp_thumbnail = link_cache.get_file_from_link(post.thumbnail)
            thumbnail_name = os.path.join(
                self.thumbnail_folder,
                f"{post.name}-thumbnail.{post.thumbnail.split('.')[-1]}",
            )
            shutil.copy2(temp_thumbnail, thumbnail_name)
            post.thumbnail = thumbnail_name
        except:
            pass

        self.queue_db_write(post)

        return post

    def get_thumbnail(self, post):
        logger.debug("Getting thumbnail for %s", post.id)
        with Dataclass_DB(PostFile, db_name=self.db_path) as post_file_db:
            if post.id in post_file_db:
                post_file = post_file_db[post.id]
                return post_file.thumbnail
        return ""

    def update_post(self, board: BOARD, post: Post):
        logger.warning("Update post called for  %s but this method is not implemented yet.", post.id)
        # No Metadata is saved...right?
        pass


if __name__ == "__main__":
    main()

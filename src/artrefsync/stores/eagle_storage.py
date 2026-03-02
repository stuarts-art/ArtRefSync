from collections import deque
from asyncio import Event
import os
from pathlib import Path
import sys
import dacite
import queue
import requests
import json
import time
from artrefsync.api.eagle_client import eagle_client
from artrefsync.boards.board_handler import PostFile
from artrefsync.models import EagleItem
from urllib import parse
from artrefsync.stores.link_cache import Link_Cache
from artrefsync.stores.storage import ImageStoreHandler, Post
from artrefsync.constants import BOARD, EAGLE, STORE, STATS
from artrefsync.config import config
from artrefsync.stats import stats
from artrefsync.api.eagle_model import EagleItem, EagleFolder, EagleLibrary
import tempfile

import logging

from artrefsync.utils.benchmark import Bm

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


def main():
    logger.info("main")
    eagle = EagleHandler()
    toupdate: list[Post] = []
    for board in eagle.board_artist_dict:
        if board == BOARD.DANBOORU:
            for artist in eagle.board_artist_dict[board]:
                print(artist)
                posts = eagle.get_posts(board, artist)
                for pid, post in posts.items():
                    if "rule34" in post.url:
                        toupdate.append(post)
                        # print(f"{artist} adding {pid}")
    print(f"Posts Requring Updates {len(toupdate)}")
    for i, post in enumerate(toupdate):
        if i % 50 == 0:
            sys.stdout.write(".")
            sys.stdout.flush()

        url = f"https://danbooru.donmai.us/posts/{post.id.split('.')[0]} "
        try:
            eagle.client.item.update(post.ext_id, url=url)
        except:
            pass


class EagleHandler(ImageStoreHandler):
    """
    Helper class for interacting with Eagle using https://api.eagle.cool/
    """

    def __init__(self):
        logger.info("Initializing Eagle Handler")
        self.artists_id = None
        self.reload_config()
        config.subscribe_reload(self.reload_config)

    def reload_config(self):
        self.library = config[STORE.EAGLE][EAGLE.LIBRARY].strip()
        self.artists_folder_name = config[STORE.EAGLE][EAGLE.ARTIST_FOLDER].strip()
        self.client = eagle_client
        self.artists_id = None
        self.folder_artist_dict = {}
        self.board_dict = {}
        self.board_artist_dict = {}

        if self.artists_folder_name == "":
            self.artists_folder_name = "artists"

        self.library_path_dict = {}
        history = self.client.library.history()
        for path in history:
            library_str = path.split("/")[-1]
            library_str = library_str.removesuffix(".library")
            self.library_path_dict[library_str] = path

        self.switch_libary(self.library)
        self.get_or_create_artist_folder()
        logger.debug("%s \n%s", "Board Artist dict:", self.board_artist_dict)

    def get_store(self):
        return STORE.EAGLE

    def post_add_from_path(self, post: Post, path: str):
        if (
            post.board not in self.board_artist_dict
            or post.artist_name not in self.board_artist_dict[post.board]
        ):
            self.create_board_and_artist_folders(
                post.board,
                [
                    post.artist_name,
                ],
            )

        artist_folder = self.board_artist_dict[post.board][post.artist_name]
        return self.client.item.post_add_from_path(
            path=path,
            name=post.name,
            website=post.website,
            tags=post.tags,
            folder_id=artist_folder,
        )

    def get_list_items(
        self, limit=10000, folders=None, post_limit=None
    ) -> list[EagleItem.Item]:
        data = []
        for offset in range(100):
            items = self.client.item.list_items(
                limit=limit, offset=offset, folders=folders
            )
            data.extend(items)
            if limit and len(items) < limit:
                break
            if post_limit and len(data) > post_limit:
                break
        return data

    def eagle_item_to_post(
        self, item: EagleItem.Item, artist_name=None, artist_board=BOARD.OTHER
    ) -> Post | None:
        pid = Post.parse_id(item.name)
        lib = self.library_path_dict[self.library]
        # dir = f"{self.library_path_dict[self.library]}/images/{item.id}.info/"
        board_path = Path(os.path.join(lib, "images", f"{item.id}.info"))
        thumbnail = "" 
        file = f"{self.library_path_dict[self.library]}/images/{item.id}.info/{item.name}.{item.ext}"
        for path in  board_path.iterdir():
            strpath = str(path)
            if "metadata.json" in strpath:
                continue
            if "thumbnail" in strpath:
                thumbnail = strpath
            else:
                file = strpath

        post = PostFile(
            id=pid,
            ext_id=item.id,  # External ID
            store=self.get_store(),
            board=None,
            preview=thumbnail,
            file=f"{self.library_path_dict[self.library]}/images/{item.id}.info/{item.name}.{item.ext}",
        )
        return post

    def create_board_and_artist_folders(self, board: BOARD, artists: list[str]):
        self.get_or_create_artist_folder()
        for artist in artists:
            self.make_board_artist_dir(board, artist)

    def make_board_artist_dir(self, board: BOARD, artist: str) -> dict[str, Post]:
        folder_created = False
        # Create board folder if not exists
        if board not in self.board_dict:
            board_folder = self.client.folder.create(board, self.artists_id)
            self.board_dict[board_folder.name] = board_folder.id
            self.board_artist_dict[board_folder.name] = {}
            folder_created = True
        # Create board folder if not exists
        if artist not in self.board_artist_dict[board]:
            artist_folder = self.client.folder.create(artist, self.board_dict[board])
            self.board_artist_dict[board][artist] = artist_folder.id
            self.folder_artist_dict[artist_folder.id] = artist
            folder_created = True
        return folder_created
        

    # Assuming that we will always call get_posts before save_posts
    def get_posts(self, board: BOARD, artist: str) -> dict[str, PostFile]:
        if self.make_board_artist_dir(board, artist):
            return {}

        limit = 10000
        data = self.get_list_items(folders=self.board_artist_dict[board][artist])
        post_files = {}
        for item in data:
            post_file = self.eagle_item_to_post(item)
            if post_file:
                post_files[post_file.id] = post_file
        logger.info(f"Eagle Items for {board}, {artist} - {len(post_files)}")
        return post_files

    def save_post(
        self, post: Post, link_cache: Link_Cache = None, event: Event = None
    ) -> str | None:
        if event and event.is_set():
            return

        if link_cache:
            # loading(link_cache.increment_store_count(self.get_store())/link_cache.get_store_missing(self.get_store()))
            response = self.post_add_from_path(
                post, link_cache.get_file_from_link(post.url)
            )
        else:
            suffix = f".{post.url.split('.')[-1]}"
            with tempfile.NamedTemporaryFile(mode="wb", suffix=suffix) as f:
                Link_Cache.download_link_to_file(post.url, tempfile)
                response = self.post_add_from_path(post, f.name)
        response.raise_for_status()
        return response

    def update_post(self, post: Post):
        eagle_client.item.update(post.ext_id, post.tags, url=post.url)

    def get_or_create_artist_folder(self):
        folders = self.client.folder.list()
        folder_q = deque((folder for folder in folders))
        # artists_folder: dict = None
        while folder_q:
            folder = folder_q.popleft()
            if folder.name == self.artists_folder_name:
                artists_folder = folder
                break

        if not artists_folder:
            logger.info("Creating Artists (Main Parent) Folder")
            artists_folder = self.client.folder.create(self.artists_folder_name)
        self.artists_id = artists_folder.id
        logger.info("Artist Folder ID: %s", artists_folder.id)

        for board in artists_folder.children:
            board_name = board.name
            self.board_dict[board_name] = board.id
            self.board_artist_dict[board_name] = {}
            for artist in board.children:
                artist_name = artist.name
                self.board_artist_dict[board_name][artist_name] = artist.id
                self.folder_artist_dict[artist.id] = artist_name

    def switch_libary(self, library_string):
        try:
            if library_string in self.library_path_dict:
                response = self.client.library.switch(
                    self.library_path_dict[library_string]
                )
                logger.info(
                    "Switch Library to %s response: %s.", library_string, response
                )
            else:
                logger.warning('Failed to find library "%s" in History', library_string)
        except Exception as e:
            logger.error(e)

    def get_thumbnail(self, post):
        return self.client.item.thumbnail(post.ext_id)
        # return super().get_thumbnail(post)



if __name__ == "__main__":
    main()

from collections import deque
from asyncio import Event
import sys
import dacite
import queue
import requests
import json
import time
from artrefsync.api.eagle_client import eagle_client
from artrefsync.models import EagleItem
from urllib import parse
from artrefsync.stores.link_cache import Link_Cache
from artrefsync.stores.storage import ImageStorage, Post
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


class EagleHandler(ImageStorage):
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
        self, item: EagleItem.Item, artist_name=None, artist_board=None
    ) -> Post | None:
        if not artist_name:
            artist_name = ""
            artist_folder = None
            for item_folder in item.folders:
                if item_folder in self.folder_artist_dict:
                    artist_name = self.folder_artist_dict[item_folder]
                    artist_folder = item_folder
                    break
            if artist_name == "":
                return None

        if not artist_board:
            artist_board = BOARD.OTHER
            for board in self.board_artist_dict:
                if artist_folder in board:
                    artist_board = board
                    break
        pid = Post.parse_id(item.name)
        ratio = None
        if item.width and item.height:
            ratio = item.width / item.height

        post = Post(
            id=pid,
            ext_id=item.id,  # External ID
            ext=item.ext,
            name=item.name,
            artist_name=artist_name,
            tags=item.tags,
            board=artist_board,
            score=0,
            url=item.url,
            website="",
            height=item.height,
            width=item.width,
            ratio=ratio,
            file=f"{self.library_path_dict[self.library]}/images/{item.id}.info/{item.name}.{item.ext}",
        )
        return post

    def get_post_tag_dict(self) -> dict[str, Post]:
        posts = {}
        for board, artist_dict in self.board_artist_dict.items():
            for artist, artist_folder in artist_dict.items():
                items: list[EagleItem] = self.get_list_items(folders=artist_folder)

                for item in items:
                    post = self.eagle_item_to_post(item, artist, board)
                    if board not in post.tags:
                        post.tags.append(board)
                    if artist not in post.tags:
                        post.tags.append(artist)
                    posts[post.id] = post
        return posts

    def create_board_and_artist_folders(self, board: BOARD, artists: list[str]):
        self.get_or_create_artist_folder()
        board = str(board)
        if board not in self.board_artist_dict:
            board_folder = self.client.folder.create(board, self.artists_id)
            self.board_artist_dict[board] = {}
            self.board_dict[board] = board_folder.id

        for artist in artists:
            if artist not in self.board_artist_dict[board]:
                artist_folder = self.client.folder.create(
                    artist, self.board_dict[board]
                )
                self.board_artist_dict[board][artist] = artist_folder.id
                self.folder_artist_dict[artist_folder.id] = artist
                time.sleep(0.01)

    # Assuming that we will always call get_posts before save_posts
    def get_posts(self, board: BOARD, artist: str) -> dict[str, Post]:
        # print(board.value)
        board = str(board)

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
            folder_created = True

        if folder_created:
            return {}

        limit = 10000
        data = self.get_list_items(folders=self.board_artist_dict[board][artist])
        posts = {}
        for item in data:
            post = self.eagle_item_to_post(item)
            if post:
                posts[post.id] = post
        logger.info(f"Eagle Items for {board}, {artist} - {len(posts)}")
        return posts

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

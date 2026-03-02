from threading import Event
import time
import requests
from bs4 import BeautifulSoup
from artrefsync.api.danbooru_client import Danbooru_Client
from artrefsync.stats import stats
from artrefsync.config import config
from artrefsync.boards.board_handler import Post, ImageBoardHandler
from artrefsync.constants import BOARD, STATS, DANBOORU
from artrefsync.disk_cache import disk_cache

import logging

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


class Danbooru_Handler(ImageBoardHandler):
    """
    Class to handle requesting and handling messages from the image board E621
    """

    def __init__(self):
        logger.info("Initialize Danbooru Handler")
        self.reload()
        config.subscribe_reload(self.reload)

        
    def reload(self):
        self.danbooru_api_key = config[BOARD.DANBOORU][DANBOORU.API_KEY]
        self.danbooru_username = config[BOARD.DANBOORU][DANBOORU.USERNAME]
        self.black_list = config[BOARD.DANBOORU][DANBOORU.BLACK_LIST]
        self.artist_list = list(set(config[BOARD.DANBOORU][DANBOORU.ARTISTS]))
        self.client = Danbooru_Client(
            self.danbooru_username, api_key=self.danbooru_api_key
        )
        self.board = BOARD.DANBOORU

    def get_artist_list(self):
        return self.artist_list

    def get_board(self) -> BOARD:
        return BOARD.DANBOORU

    # @disk_cache
    def get_posts(self, tag, post_limit=None, stop_event: Event=None) -> dict[str, Post]:
        posts = {}

        danbooru_posts = self.client.get_posts(tag, post_limit)
        if stop_event and stop_event.is_set():
            return None
        if " " in tag:
            tag = tag.split()[0]  # Remove query and metatags
        logger.info("Recieved %s from client.", len(danbooru_posts))

        for dpost in danbooru_posts:
            website = f"https://danbooru.donmai.us/posts/{dpost.id}"
            post_id = Post.make_storage_id(dpost.id, self.get_board())
            is_black_listed = False
            tags = dpost.tag_string

            tags.append(f"rating_{dpost.rating}")
            tags.append(f"{self.get_board().value}")
            tags.append(dpost.file_ext)

            for black_listed in self.black_list:
                if black_listed in tags:
                    stats.add(STATS.SKIP_COUNT, 1)
                    print(f"Skipping {post_id} for {black_listed}. ({website})")
                    is_black_listed = True
                    break
            if is_black_listed:
                continue

            post = Post(
                id=post_id,
                ext_id=dpost.id,
                name=f"{post_id}-{tag}",
                artist_name=tag,
                tags=tags,
                board=self.board,
                board_update_str=dpost.updated_at,
                score=dpost.score,
                url=dpost.file_url,
                website=website,
                height=dpost.image_height,
                width=dpost.image_width,
                ratio=dpost.image_width / dpost.image_height
                if dpost.image_width and dpost.image_height
                else None,
                sample_link=dpost.large_file_url,
                ext=dpost.file_ext,
                file_link="",
            )
            stats.add(STATS.TAG_SET, dpost.tag_string)
            stats.add(STATS.TAG_SET, tag)
            stats.add(STATS.ARTIST_SET, tag)
            posts[post_id] = post
            stats.add(STATS.POST_COUNT)
        return posts


danbooru_handler = Danbooru_Handler()

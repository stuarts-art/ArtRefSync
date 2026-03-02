from threading import Event
import time
import requests
from bs4 import BeautifulSoup
from artrefsync.api.r34_model import R34_Post
from artrefsync.api.r34_client import R34_Client
from artrefsync.stats import stats
from artrefsync.config import config
from artrefsync.boards.board_handler import Post, ImageBoardHandler
from artrefsync.constants import BOARD, R34, STATS
from artrefsync.disk_cache import disk_cache

import logging

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


class R34Handler(ImageBoardHandler):
    """
    Class to handle requesting and handling messages from the image board E621
    """

    def __init__(self):
        logger.info("Initialize R34 Handler")
        self.reload()
        config.subscribe_reload(self.reload)

        
    def reload(self):
        self.r34_api_string = config[BOARD.R34][R34.API_KEY]
        self.black_list = config[BOARD.R34][R34.BLACK_LIST]
        self.artist_list = list(set(config[BOARD.R34][R34.ARTISTS]))
        self.client = R34_Client(self.r34_api_string)
        self.board = BOARD.R34

    def get_artist_list(self):
        return self.artist_list

    def get_board(self) -> BOARD:
        return BOARD.R34

    @disk_cache
    def get_posts(self, tag, post_limit=None, stop_event: Event = None) -> dict[str, Post]:
        posts = {}

        r34_posts: list[R34_Post] = self.client.get_posts(tag, post_limit, stop_event)
        if stop_event and stop_event.is_set():
            return None

        if " " in tag:
            tag = tag.split()[0]  # Remove query and metatags
        logger.info("Recieved %s from client.", len(r34_posts))

        for rpost in r34_posts:
            skip_rpost = False
            website = f"https://rule34.xxx/index.php?page=post&s=view&id={rpost.id}"
            post_id = Post.make_storage_id(rpost.id, self.get_board())

            tags = rpost.tags
            tags.append(f"rating_{rpost.rating}")
            for black_listed in self.black_list:
                if black_listed in rpost.tags:
                    stats.add(STATS.SKIP_COUNT, 1)
                    print(f"Skipping {post_id} for {black_listed}. ({website})")
                    skip_rpost = True
                    break
            if skip_rpost:
                continue

            ext=rpost.file_url.split(".")[-1]
            post = Post(
                id=post_id,
                ext_id=rpost.id,
                name=f"{post_id}-{tag}",
                artist_name=tag,
                tags=rpost.tags,
                board=self.board,
                score=rpost.score,
                url=rpost.file_url,
                website=website,
                board_update_str=rpost.change,
                height=rpost.height,
                width=rpost.width,
                ratio=rpost.width / rpost.height
                if rpost.width and rpost.height
                else None,
                sample_link=rpost.sample_url,
                preview_link=rpost.preview_url,
                file_link=rpost.file_url,
                ext=ext,
            )
            stats.add(STATS.TAG_SET, rpost.tags)
            stats.add(STATS.TAG_SET, tag)
            stats.add(STATS.ARTIST_SET, tag)
            posts[post_id] = post
            stats.add(STATS.POST_COUNT)
        return posts


# r34_handler = R34Handler()

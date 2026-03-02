from threading import Event
import time
import base64
import json
import requests
from artrefsync.api.e621_client import E621_Client
from artrefsync.api.e621_model import E621_Post
from artrefsync.config import config
from artrefsync.stats import stats
from artrefsync.boards.board_handler import Post, ImageBoardHandler
from artrefsync.constants import STATS, BOARD, E621, TABLE
from artrefsync.disk_cache import disk_cache

import logging

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


class E621Handler(ImageBoardHandler):
    """Class to handle messages from the image board E621"""

    def __init__(self):
        logger.info("Initialize E621 Handler")
        self.reload()
        config.subscribe_reload(self.reload)

    def reload(self):
        username = config[BOARD.E621][E621.USERNAME]
        api_key = config[BOARD.E621][E621.API_KEY]
        self.black_list = config[BOARD.E621][E621.BLACK_LIST]
        self.artist_list = list(set(config[BOARD.E621][E621.ARTISTS]))

        self.client = E621_Client(username, api_key)
        self.website = "https://e621.net/posts.json"
        self.hostname = "e621.net"
        self.limit = 320
        user_string = f"{username}:{api_key}"
        self.website_headers = {
            "Authorization": f"Basic {base64.b64encode(user_string.encode('utf-8')).decode('utf-8')}",
            "User-Agent": f"MyProject/1.0 (by {username} on e621)",
        }

    def get_board(self) -> BOARD:
        return BOARD.E621

    def get_artist_list(self):
        # return  list(set(config[BOARD.E621][E621.ARTISTS]))
        return self.artist_list

    @disk_cache
    def get_posts(self, tag, post_limit=None, stop_event: Event=None) -> dict[str, Post]:
        post_dict = {}
        e621_posts: list[E621_Post]= self.client.get_posts(tag, post_limit)
        if stop_event and stop_event.is_set():
            return None
        if " " in tag:
            tag = tag.split()[0]  # Remove query and metatags

        for e_post in e621_posts:
            tags = []
            general = e_post.tags.general
            species = e_post.tags.species
            artists = e_post.tags.artist
            franchise = e_post.tags.copyright
            character = e_post.tags.character
            meta = e_post.tags.meta
            rating = f"rating_{e_post.rating.value}"
            pools = [f"pool_e621_{pool_id}" for pool_id in e_post.pools]
            tags = general + species + artists + franchise + character + meta + [rating, e_post.file.ext, tag, ] + pools

            pid = Post.make_storage_id(e_post.id, self.get_board())
            name = f"{pid}-{tag}"
            url = e_post.file.url
            website = f"https://e621.net/posts/{e_post.id}"
            post_id = Post.make_storage_id(e_post.id, self.get_board())

            is_black_listed = False
            for black_listed in self.black_list:
                if black_listed in tags:
                    stats.add(STATS.SKIP_COUNT, 1)
                    logger.debug(
                        "Skipping %s for blacklist item '%s'. %s",
                        post_id,
                        black_listed,
                        website,
                    )
                    is_black_listed = True
                    break
            if is_black_listed:
                continue

            height = e_post.file.height
            width = e_post.file.width
            ratio = None
            if height and width:
                ratio = height / width
            post = Post(
                id=pid,
                ext_id=e_post.id,
                name=name,
                artist_name=tag,
                tags=tags,
                score=e_post.score.up,
                url=url,
                board_update_str=e_post.updated_at,
                website=website,
                height=height,
                width=width,
                ratio=ratio,
                ext=e_post.file.ext,
                board=self.get_board(),
                file_link=e_post.file.url,
                sample_link=e_post.sample.url,
                preview_link=e_post.preview.url,
            )
            stats.add(STATS.TAG_SET, tags)
            stats.add(STATS.SPECIES_SET, species)
            stats.add(STATS.ARTIST_SET, artists)
            stats.add(STATS.COPYRIGHT_SET, franchise)
            stats.add(STATS.CHARACTER_SET, character)
            stats.add(STATS.META_SET, meta)
            stats.add(STATS.RATING_SET, rating)
            post_dict[pid] = post
            stats.add(STATS.POST_COUNT)
        return post_dict


e621_handler = E621Handler()


from threading import Event
import time
import requests
from bs4 import BeautifulSoup
from artrefsync.api.r34_model import R34_Post, parse_r34_post
from artrefsync.config import config
from artrefsync.constants import TABLE, R34
from artrefsync.disk_cache import disk_cache
from dataclasses import asdict

import logging

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)

class R34_Client:
    """
    Class to handle requesting and handling messages from the image board E621
    """

    def __init__(self, api_string=None):
        self.r34_api_string = (
            api_string if api_string else config[TABLE.R34][R34.API_KEY]
        )
        self.base_url = "https://api.rule34.xxx/index.php?page=dapi&s=post&q=index"
        self.hostname = "rule34.xxx"
        self.limit = 1000
        self.retries = 3
        self.last_run = 0
        self.black_list = [f" -{x}" for x in config[TABLE.R34][R34.BLACK_LIST]]

    def _build_url_request(self, tag, page) -> str:
        return f"{self.base_url}{self.r34_api_string}&limit={self.limit}&tags={tag}{''.join(self.black_list)}&pid={page}"

    # Translates XML -> DICT -> R34_Post
    @disk_cache
    def get_posts(self, tag, post_limit=None, stop_event: Event = None) -> list[R34_Post]:
        posts = []
        self.last_run = time.time() - 1

        for page in range(10):
            if stop_event and stop_event.is_set():
                return None
            if time.time() - self.last_run < 0.6:
                time.sleep(time.time() - self.last_run)
            self.last_run = time.time()
            response = requests.get(self._build_url_request(tag, page), timeout=2.0)
            soup = BeautifulSoup(response.content, features="xml")
            found_posts = soup.find_all("post")
            logger.info("Found %s posts.", len(found_posts))

            for p in found_posts:
                r34_post = parse_r34_post(p.attrs)
                posts.append(r34_post)
                if post_limit and post_limit < len(posts):
                    break
            if post_limit and post_limit < len(posts):
                break

            if len(found_posts) < self.limit:
                break

        return posts
# client = R34_Client()
# print(client.get_posts("", 1))

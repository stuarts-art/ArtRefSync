import json
import logging
import re
import time
from threading import Event

import requests
from dacite import DaciteError
from tenacity import retry, stop_after_attempt, wait_exponential

from artrefsync.api.danbooru_model import (
    Danbooru_Post,
)
from artrefsync.config import cache, config
from artrefsync.constants import DANBOORU, TABLE
from artrefsync.db.post_db import PostDb

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


def main():
    pass

class Danbooru_Client:
    """
    Class to handle requesting and handling messages from the image board E621
    """

    def __init__(self, username=None, api_key=None, only_recent=False):
        logger.info("Creating Danbooru Client")
        self.username = (
            username if username else config[TABLE.DANBOORU][DANBOORU.USERNAME]
        )
        self.api_key = (
            username if username else config[TABLE.DANBOORU][DANBOORU.API_KEY]
        )
        self.website_headers = {
            "User-Agent": f"ArtRefSync/1.0 ({username})",
        }
        self.only_recent = only_recent
        self.base_url = "https://danbooru.donmai.us"
        self.post_base_url = f"{self.base_url}/posts.json"
        self.tags_base_url = f"{self.base_url}/tags.json"
        self.hostname = "danbooru.domai.us"
        self.limit = 200
        self.retries = 3
        self.last_run = time.time()

    def _build_post_url_request(self, tag, page, last_id) -> str:
        url_request = f"{self.post_base_url}?tags={tag}{f'+id:>{last_id}' if last_id else ''}&limit={self.limit}&page={page}"
        return url_request

    def _build_tag_url_request(self, tag, limit=10) -> str:
        url_request = f"{self.tags_base_url}?search[name_matches]={tag}&search[order]=count&limit={limit}"
        return url_request

    def get_posts(
        self, tag, post_limit=10000, stop_event: Event = Event()
    ) -> list[Danbooru_Post]:
        logger.debug("Getting posts for %s", tag)

        if "+limit:" in tag:
            limit = int(re.split("\rD+", tag.split("limit:")[-1])[0])
            if limit:
                post_limit = limit

        posts: list[Danbooru_Post] = []
        failed = []
        skipped = []

        last_id = None
        if self.only_recent:
            with PostDb() as post_db:
                last_id = post_db.get_last_id(tag, TABLE.DANBOORU)
        # Starts at index 1 (Index 0 returns page 1)
        posts_data = []
        for page in range(1, 20):
            if stop_event and stop_event.is_set():
                return []
            page_data = self.get_page(tag, page, last_id)
            posts_data.extend(page_data)
            logger.debug("%s - Page %d, %d", tag, page, len(page_data))
            if len(page_data) < self.limit:
                logger.debug(f"Page {page} Breaking Loop")
                break
            if len(posts) > post_limit:
                break
        for post_data in posts_data:
            try:
                post = Danbooru_Post.parse_danbooru_post(post_data)
                if post.is_deleted:
                    skipped.append(post_data["id"])
                    continue
                else:
                    posts.append(post)
            except DaciteError as e:
                logger.debug(e)
                failed = post_data
            if len(posts) >= post_limit:
                break

        if skipped:
            logger.debug("%i posts skipped.", len(skipped))
        if failed:
            logger.debug("%i posts failed.", len(failed))

        return posts

    @cache.memoize(expire=config.cache_ttl())
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1))
    def get_page(self, tag: str, page: int, last_id):
        delta_time = time.time() - self.last_run
        if delta_time < 0.1:
            time.sleep(0.1 - delta_time)
        response = requests.get(
            self._build_post_url_request(tag, page, last_id),
            headers=self.website_headers,
            timeout=5.0,
        )
        response.raise_for_status()
        post_data = json.loads(response.content)
        self.last_run = time.time()
        return post_data


if __name__ == "__main__":
    main()

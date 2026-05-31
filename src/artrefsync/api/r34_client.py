import json
import logging
from threading import Event
import re

import requests
from requests_ratelimiter import LimiterSession
from tenacity import retry, stop_after_attempt, wait_exponential

from artrefsync.config import config
from artrefsync.api.r34_model import R34_Post
from artrefsync.constants import R34, TABLE
from artrefsync.db.post_db import PostDb


logger = logging.getLogger(__name__)


def main():
    pass


class R34_Client:
    """
    Class to handle requesting and handling messages from the image board E621
    """

    def __init__(self, api_string=None, only_recent=False, stop_event:Event = None):
        logger.info("R34 Init Start")


        self.r34_api_string = (
            api_string if api_string else config[TABLE.R34][R34.API_KEY]
        )
        self.session = LimiterSession(per_minute=60)
        self.only_recent = only_recent
        self.base_url = "https://api.rule34.xxx/index.php?page=dapi&s=post&q=index"
        self.hostname = "rule34.xxx"
        self.limit = 200
        self.retries = 3
        self.last_run = 0
        self.black_list = [f" -{x}" for x in config[TABLE.R34][R34.BLACK_LIST]]
        logger.info("R34 Init Complete")
        self.stop_event = stop_event

    def _build_url_request(self, tag, page, last_id=None) -> str:
        return f"{self.base_url}{self.r34_api_string}&limit={self.limit}&tags={tag}{f'+id:>{last_id}' if last_id else ''}&fields=tag_info&pid={page}&json=1"

    async def get_posts(
        self, tag, post_limit=10000
    ) -> list[R34_Post]:
        posts = []
        posts_data = []
        last_id = None
        if "+limit:" in tag:
            limit = int(re.split("\rD+", tag.split("limit:")[-1])[0])
            if limit:
                post_limit = limit

        if self.only_recent:
            with PostDb() as post_db:
                last_id = post_db.get_last_id(tag, "r34")
        for page in range(50):
            if self.stop_event and self.stop_event.is_set():
                return None
            page_data = self.get_page(tag, page, last_id)
            posts_data.extend(page_data)
            logger.debug("%s - Page %d, %d", tag, page, len(page_data))
            if len(page_data) < self.limit:
                break
        for post_data in posts_data:
            try:
                r34_post = R34_Post.parse_r34_post(post_data)
                posts.append(r34_post)
            except Exception as e:
                logger.exception("Failed to parse")
                pass

            if post_limit and len(posts) >= post_limit:
                break
        return posts

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1))
    # @config.cache("r34").memoize(expire=config.cache_ttl())
    def get_page(self, tag, page, last_id=None):
        response = self.session.get(
            self._build_url_request(tag, page, last_id), timeout=2.0
        )
        response.raise_for_status()
        page_data = json.loads(response.content)
        return page_data


if __name__ == "__main__":
    main()

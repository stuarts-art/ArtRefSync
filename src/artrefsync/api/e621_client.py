import base64
import json
import logging
import re
from threading import Event

import requests
from dacite import DaciteError

from tenacity import retry, stop_after_attempt, wait_exponential

from artrefsync.api.e621_model import E621_Post
from artrefsync.config import cache, config
from artrefsync.constants import E621, TABLE
from artrefsync.db.post_db import PostDb

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


def main():
    pass


class E621_Client:
    def __init__(self, username: str = None, api_key: str = None, only_recent=False):
        logger.info("E621 Client Init")
        if not username:
            username = config[TABLE.E621][E621.USERNAME]
        if not api_key:
            api_key = config[TABLE.E621][E621.API_KEY]
        user_string = f"{username}:{api_key}"
        self.website_headers = {
            "Authorization": f"Basic {base64.b64encode(user_string.encode('utf-8')).decode('utf-8')}",
            "User-Agent": f"MyProject/1.0 (by {username} on e621)",
        }
        self.only_recent = only_recent

        self.website = "https://e621.net/posts.json"
        self.hostname = "e621.net"
        self.limit = 320
        logger.info("E621 Client Complete")

    def _build_website_parameters(self, page, tag, last_id=None) -> str:
        return f"{self.website}?limit={self.limit}&tags={tag}{f'+id:>{last_id}' if last_id else ''}&page={page}"

    def get_posts(
        self, tags: str, post_limit=10000, stop_event: Event = None
    ) -> list[E621_Post]:
        if "+limit:" in tags:
            limit = int(re.split("\rD+", tags.split("limit:")[-1])[0])
            if limit:
                post_limit = limit

        last_id = None
        if self.only_recent:
            with PostDb() as post_db:
                last_id = post_db.get_last_id(tags, "e621")

        posts = []
        posts_data = []
        for page in range(1, 50):  # handle pagination
            page_data = self.get_page(tags, page, last_id)
            logger.debug(f"{tags}, Page: {page}, Count: {len(page_data)}")
            posts_data.extend(page_data)
            if len(page_data) < self.limit or len(posts_data) >= post_limit:
                break
            if stop_event and stop_event.is_set():
                return None

        for post_data in posts_data:
            try:
                if (post := E621_Post.parse_e621_post(post_data)) is not None:
                    posts.append(post)
            except DaciteError as e:
                logger.error(e)

            if len(posts) >= post_limit:
                break

        logger.info("E621 Client GetPosts for tags=%s len = %s, ", tags, len(posts))
        return posts

    @cache.memoize(expire=config.cache_ttl())
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1))
    def get_page(self, tags, page, last_id=None):

        logger.debug("CACHE MISS")
        request_params = self._build_website_parameters(page, tags, last_id=last_id)
        response = requests.get(
            request_params,
            headers=self.website_headers,
            timeout=10,
        )
        response.raise_for_status()
        page_data = json.loads(response.content)["posts"]
        return page_data


if __name__ == "__main__":
    main()

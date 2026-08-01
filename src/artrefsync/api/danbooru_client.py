import json
import logging
import re
import time
from threading import Event

from dacite import DaciteError
from requests_ratelimiter import LimiterSession
from tenacity import retry, stop_after_attempt, wait_exponential

from artrefsync.api.danbooru_model import (
    Danbooru_Post,
)
from artrefsync.config import get_config
config = get_config()
from artrefsync.constants import DANBOORU, TABLE

logger = logging.getLogger(__name__)


def main():
    client = Danbooru_Client()
    pass

class Danbooru_Client:
    """
    Class to handle requesting and handling messages from the image board E621
    """

    def __init__(self, username=None, api_key=None, only_recent=False, stop_event:Event = None):
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
        self.session = LimiterSession(per_second=10)
        self.only_recent = only_recent
        self.stop_event = stop_event
        self.base_url = "https://danbooru.donmai.us"
        self.post_base_url = f"{self.base_url}/posts.json"
        self.tags_base_url = f"{self.base_url}/tags.json"
        self.hostname = "danbooru.domai.us"
        self.limit = 200
        self.retries = 3
        self.last_run = time.time()

    def _build_post_url_request(self, tag, page = 1, last_id = None) -> str:
        url_request = f"{self.post_base_url}?tags={tag}{f'+id:>{last_id}' if last_id else ''}&limit={self.limit}&page={page}"
        return url_request

    def _build_tag_url_request(self, tag, limit=10) -> str:
        url_request = f"{self.tags_base_url}?search[name_matches]={tag}&search[order]=count&limit={limit}"
        return url_request

    def get_posts(
        self, tag, post_limit=10000, last_id = None
    ) -> list[Danbooru_Post]:
        logger.debug("Getting posts for %s", tag)

        if "+limit:" in tag:
            limit = int(re.split("\rD+", tag.split("limit:")[-1])[0])
            if limit:
                post_limit = limit

        posts: list[Danbooru_Post] = []
        failed = []
        skipped = []

        # Starts at index 1 (Index 0 returns page 1)
        posts_data = []
        for page in range(1, 20):
            if self.stop_event and self.stop_event.is_set():
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

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1))
    # @config.cache("danbooru").memoize(expire=config.cache_ttl())
    def get_page(self, tag: str, page: int=1, last_id = "", order = ""):
        tags = [tag]
        if last_id:
            tags.append(f"id:>{last_id}")
        if order:
            tags.append(f"order:{order}")

        params = {
            "tags": "+".join(tags),
            "limit": self.limit,
            "page": page
        }

        response = self.session.get(
            self.post_base_url,
            params=params,
            headers=self.website_headers,
            timeout=5.0,
        )
        response.raise_for_status()
        post_data = json.loads(response.content)
        self.last_run = time.time()
        return post_data


if __name__ == "__main__":
    main()

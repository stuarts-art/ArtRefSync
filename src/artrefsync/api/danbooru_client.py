import base64
import json
import logging
import re
from threading import Event
import dacite
import requests
from dacite import DaciteError
from ratelimit import limits
from tenacity import retry, stop_after_attempt, wait_exponential

from artrefsync.api.danbooru_model import (
    Danbooru_Post,
    Danbooru_Tag,
    parse_danbooru_post,
)
from artrefsync.config import cache, config
from artrefsync.constants import DANBOORU, TABLE
from artrefsync.db import PostDb

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
        self.website_headers = None
        if not username:
            username = config[TABLE.DANBOORU][DANBOORU.USERNAME]
        if not api_key:
            api_key = config[TABLE.DANBOORU][DANBOORU.API_KEY]
        if username and api_key:
            user_string = f"{username}:{api_key}"
            self.website_headers = {
                "Authorization": f"Basic {base64.b64encode(user_string.encode('utf-8')).decode('utf-8')}",
            }
        self.only_recent = only_recent
        self.base_url = "https://danbooru.donmai.us"
        self.post_base_url = f"{self.base_url}/posts.json"
        self.tags_base_url = f"{self.base_url}/tags.json"
        self.hostname = "danbooru.domai.us"
        self.limit = 200
        self.retries = 3

    def _build_post_url_request(self, tag, page, last_id) -> str:
        url_request = f"{self.post_base_url}?tags={tag}{f'+id:>{last_id}' if last_id else ''}&limit={self.limit}&page={page}"
        return url_request

    def _build_tag_url_request(self, tag, limit=10) -> str:
        url_request = f"{self.tags_base_url}?search[name_matches]={tag}&search[order]=count&limit={limit}"
        return url_request

    def get_posts(
        self, tag, post_limit=10000, stop_event: Event = None
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
                return None
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
                post = parse_danbooru_post(post_data)
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

    @limits(calls=10, period=1)
    def get_tag(self, tag) -> list[Danbooru_Tag]:
        tag_dicts = self.get_tag_info(f"{tag}*")
        default_tag = None
        for tag_dict in tag_dicts:
            dtag = dacite.from_dict(Danbooru_Tag, tag_dict)
            if dtag.name == tag:
                return dtag
            elif default_tag is None:
                default_tag = dtag
        return default_tag

    @limits(calls=10, period=1)
    def get_tag_info(self, tag: str):

        response = requests.get(
            self._build_tag_url_request(tag),
            headers=self.website_headers,
            timeout=5.0,
        )

        post_data = json.loads(response.content)
        return post_data

    @cache.memoize(expire=config.cache_ttl())
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1))
    @limits(calls=10, period=1)
    def get_page(self, tag: str, page: int, last_id):
        response = requests.get(
            self._build_post_url_request(tag, page, last_id),
            headers=self.website_headers,
            timeout=5.0,
        )
        response.raise_for_status()
        post_data = json.loads(response.content)
        return post_data


if __name__ == "__main__":
    main()

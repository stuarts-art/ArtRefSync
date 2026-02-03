import base64
import json
from threading import Event
import time
import requests
from dacite.exceptions import MissingValueError
from artrefsync.api.danbooru_model import Danbooru_Post, parse_danbooru_post
from artrefsync.config import config
from artrefsync.constants import DANBOORU, TABLE

import logging

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


class Danbooru_Client:
    """
    Class to handle requesting and handling messages from the image board E621
    """

    def __init__(self, username=None, api_key=None):
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
        self.base_url = "https://danbooru.donmai.us/posts.json?tags="
        self.hostname = "danbooru.domai.us"
        self.limit = 200
        self.retries = 3
        self.last_run = 0

    def _build_url_request(self, tag, page) -> str:
        return f"{self.base_url}&limit={self.limit}&tags={tag}&page={page}"

    # @disk_cache
    def get_posts(
        self, tag, post_limit=None, stop_event: Event = None
    ) -> list[Danbooru_Post]:
        logger.info("Getting posts for %s", tag)
        if time.time() - self.last_run < 0.6:
            time.sleep(time.time() - self.last_run)
        self.last_run = time.time()

        posts: list[Danbooru_Post] = []
        self.last_run = time.time() - 1
        failed = []
        skipped = []

        # Starts at index 1 (Index 0 returns page 1)
        for page in range(1, 20):
            if stop_event and stop_event.is_set():
                return None
            response_count = self.get_page(tag, page, posts, failed, skipped)
            if response_count < self.limit:
                logger.debug(f"Page {page} Breaking Loop")
                break
        if skipped:
            logger.debug("%i posts skipped.", len(skipped))
        
        logger.info("Returning %i posts for %s", len(posts), tag)
        return posts

    def get_page(self, tag: str, page: int, posts: list, failed: list, skipped: list):
        if time.time() - self.last_run < 1:
            time.sleep(1 - (time.time() - self.last_run))
        self.last_run = time.time()
        for retry in range(1, 4):
            try:
                response = requests.get(
                    self._build_url_request(tag, page),
                    headers=self.website_headers,
                    timeout=5.0,
                )
                response.raise_for_status()
                break
            except Exception as e:
                logger.warning(
                    "Request (%i / %i) for %s page %s Failed. Exception: ",
                    retry,
                    3,
                    tag,
                    page,
                    e,
                )
                if retry == 3:
                    raise e
                else:
                    time.sleep(0.6 * (retry + 1))

        response_content_dict = json.loads(response.content)
        logger.info(
            f"Artist: {tag}, Page:{page} Response Count: {len(response_content_dict)}"
        )
        for post in response_content_dict:
            try:
                parsed = parse_danbooru_post(post)
                if parsed.is_deleted:
                    skipped.append(post["id"])
                    continue

                # page_posts.append(parsed)
                posts.append(parsed)
            except (TypeError, MissingValueError):
                logger.debug("Failed to translate %s", post["id"])
                skipped.append(post["id"])

        return len(response_content_dict)

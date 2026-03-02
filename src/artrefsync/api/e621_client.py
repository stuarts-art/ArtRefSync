import base64
import logging
import json
from threading import Event
import time
import requests
from artrefsync.api.e621_model import E621_Post
from artrefsync.disk_cache import disk_cache
from artrefsync.config import config

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


class E621_Client:
    def __init__(self, username, api_key):
        if username and api_key:
            user_string = f"{username}:{api_key}"
            self.website_headers = {
                "Authorization": f"Basic {base64.b64encode(user_string.encode('utf-8')).decode('utf-8')}",
                "User-Agent": f"MyProject/1.0 (by {username} on e621)",
            }
        else:
            user_string = None
            self.website_headers = None

        self.website = "https://e621.net/posts.json"
        self.hostname = "e621.net"
        self.limit = 320
        self.last_run = 0

    def _build_website_parameters(self, page, tag) -> str:
        return f"{self.website}?limit={self.limit}&tags={tag}&page={page}"

    # @disk_cache
    def get_posts(self, tags: str, post_limit=None, stop_event: Event=None) -> list[E621_Post]:
        posts = []
        oldest_id = ""
        for page in range(1, 50):  # handle pagination
            logger.info(f"{tags} - Page {page}")
            if stop_event and stop_event.is_set():
                return None
            # Very minimal rate limiter
            if time.time() - self.last_run < 0.6:
                time.sleep(time.time() - self.last_run)
            self.last_run = time.time()

            response = requests.get(
                self._build_website_parameters(page, tags),
                headers=self.website_headers,
                timeout=10,
            )
            response.raise_for_status()
            page_data = json.loads(response.content)["posts"]

            if len(page_data) == 0:
                break
            if page != 1:
                if len(page_data) < self.limit or (oldest_id == page_data[-1]["id"]):
                    break
            oldest_id = page_data[-1]["id"]

            for post_data in page_data:
                post = E621_Post(**post_data)
                posts.append(post)
                if post_limit and post_limit < len(posts):
                    break
            if post_limit and post_limit < len(posts):
                break

        logger.info("E621 Client GetPosts for tags=%s len = %s, ", tags, len(posts))
        return posts


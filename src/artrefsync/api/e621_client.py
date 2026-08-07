import base64
import json
import logging
from threading import Event

from dacite import DaciteError
from requests_ratelimiter import LimiterSession
from tenacity import retry, stop_after_attempt, wait_exponential

from artrefsync.api.e621_model import E621_Post
from artrefsync.config import get_config
from artrefsync.constants import E621, TABLE

config = get_config()
logger = logging.getLogger(__name__)


class E621_Client:
    def __init__(
        self,
        username: str | None = None,
        api_key: str | None = None,
        only_recent=False,
        stop_event: Event | None = None,
    ):
        logger.info("E621 Client Init")
        self.website = "https://e621.net/posts.json"
        self.hostname = "https://e621.net/"
        self.limit = 320
        self.stop_event: Event = stop_event
        self.session = LimiterSession(per_second=2)
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

        logger.info("E621 Client Complete")

    def get_posts(
        self, tags: str = "", post_limit=10000, last_id=None
    ) -> list[E621_Post]:

        posts = []
        for page in range(1, 50):  # handle pagination
            if self.stop_event and self.stop_event.is_set():
                return None
            page_data = self.get_posts_page(tags, page, last_id)
            posts.extend(page_data)
            if len(page_data) < self.limit or len(posts) >= post_limit:
                break
        posts = posts[:post_limit]
        logger.info("E621 Client GetPosts for tags=%s len = %s, ", tags, len(posts))
        return posts

    @config.cache("e621").memoize(expire=config.cache_ttl())
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1))
    def get_posts_page(
        self, tags: list[str] | str = "", page=1, last_id="", order="", limit=320
    ) -> list[E621_Post]:
        logger.info("For Tag %s Getting Page %d", tags, page)
        tag_param = []
        if tags:
            tag_param.append(tags)
        if last_id:
            tag_param.append(f"id:>{last_id}")
        if order:
            tag_param.append(f"order:{order}")
        params = [("limit", limit), ("tags", "+".join(tag_param)), ("page", page)]
        response = self.session.get(
            self.website,
            params=params,
            headers=self.website_headers,
            timeout=10,
        )
        response.raise_for_status()
        page_data = json.loads(response.content)["posts"]
        posts = []
        for data in page_data:
            try:
                if (post := E621_Post.parse_e621_post(data)) is not None:
                    posts.append(post)
            except DaciteError as e:
                logger.error(e)
        return posts

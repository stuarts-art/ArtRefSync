import json
import logging
import re
from threading import Event

from requests_ratelimiter import LimiterSession

from artrefsync.api.r34_model import R34_Post
from artrefsync.config import get_config
from artrefsync.constants import R34, TABLE

config = get_config()
logger = logging.getLogger(__name__)


class R34_Client:
    """
    Class to handle requesting and handling messages from the image board E621
    """

    def __init__(
        self, api_string=None, only_recent=False, stop_event: Event | None = None
    ):
        logger.info("R34 Init Start")

        self.r34_api_string = (
            api_string if api_string else config[TABLE.R34][R34.API_KEY]
        )
        self.session = LimiterSession(per_minute=60)
        self.only_recent = only_recent
        self.base_url = "https://api.rule34.xxx/index.php"
        self.hostname = "rule34.xxx"
        self.limit = 200
        self.retries = 3
        self.last_run = 0
        self.black_list = [f" -{x}" for x in config[TABLE.R34][R34.BLACK_LIST]]

        self.api_key = ""
        self.user_id = ""
        if split_api := self.r34_api_string[:].split("&"):
            if len(split_api) != 3:
                pass
            api_str:str = split_api[1]
            user_id_str:str = split_api[2]
            if "=" in api_str:
                self.api_key = api_str.split("=", 1)[1]
            if "=" in user_id_str:
                self.user_id = user_id_str.split("=", 1)[1]
                
        logger.info("R34 Init Complete.")
        self.stop_event = stop_event


    def get_posts(self, tags: str | list[str], post_limit=10000, last_id=None) -> list[R34_Post]:
        logger.debug("Request for metadata for tags: %s", tags)
        posts = []
        posts_data = []
        tag_list = []
        last_id = int(last_id) if last_id else 0

        if isinstance(tags, str):   
            tags = tags.split()
        if last_id:
            tags.append(f"id:>{last_id}")

        for tag in tags:
            if "+limit:" in tag:
                limit = int(re.split("\rD+", tags.split("limit:")[-1])[0])
                if limit:
                    post_limit = limit
            else:
                tag_list.append(tag)

        for page in range(50):
            if self.stop_event and self.stop_event.is_set():
                return None
            page_data = self.get_page(tag_list, page)
            posts_data.extend(page_data)
            logger.debug("%s - Page %d, %d", tag_list, page, len(page_data))
            if len(page_data) < self.limit:
                break
            
        for post_data in posts_data:
            try:
                r34_post = R34_Post.parse_r34_post(post_data)
                posts.append(r34_post)
            except Exception:
                logger.exception("Failed to parse")
            if post_limit and len(posts) >= post_limit:
                break
        return posts


    def get_page(self, tag_list, page):
        params = [
            ("page", "dapi"), 
            ("s", "post"), 
            ("q", "index"), 
            ("api_key", self.api_key),
            ("user_id", self.user_id),
            ("limit", self.limit), 
            ("tags", " ".join(tag_list)),
            ("fields", "tag_info"),
            ("pid", page),
            ("json", 1)
            ]
        response = self.session.get(
            self.base_url, params=params,timeout=2.0
        )
        response.raise_for_status()
        if content:= response.content:
            page_data = json.loads(content)
        else:
            page_data = []
        return page_data

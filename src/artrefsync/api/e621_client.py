import base64
import json
import time
import requests
from artrefsync.api.e621_model import E621_Post
import logging

logger = logging.getLogger(__name__)



class E621_Client():

    def __init__(self, username, api_key):
        user_string = f"{username}:{api_key}"
        self.website_headers = {
            "Authorization": f'Basic {base64.b64encode(user_string.encode("utf-8")).decode("utf-8")}',
            "User-Agent": f"MyProject/1.0 (by {username} on e621)",
        }
        self.website = "https://e621.net/posts.json"
        self.hostname = "e621.net"
        self.limit = 320
        self.last_run = time.time()

    def _build_website_parameters(self, page, tag) -> str:
        return f"{self.website}?limit={self.limit}&tags={tag}&page={page}"

    def get_posts(self, tags:str) -> list[E621_Post]:
        posts = []
        # for page in range(1, 50):  # handle pagination
        for page in range(1, 50):  # handle pagination
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

            curr_time = time.time() - self.last_run
            if curr_time < .6:
                time.sleep(.6-curr_time)
        return posts


if __name__ == "__main__":
    main()
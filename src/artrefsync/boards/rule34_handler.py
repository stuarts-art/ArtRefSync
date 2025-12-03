import time
import requests
from bs4 import BeautifulSoup
import artrefsync.stats as stats
from artrefsync.config import Config
from artrefsync.boards.board_handler import Post, ImageBoardHandler
from artrefsync.constants import BOARD, R34, STATS

class R34Handler(ImageBoardHandler):
    """
    Class to handle requesting and handling messages from the image board E621
    """
    def __init__(self, config:Config):
        self.r34_api_string = config.getR34(R34.API_KEY)
        self.black_list = config.getR34(R34.BLACK_LIST)
        self.base_url = "https://api.rule34.xxx/index.php?page=dapi&s=post&q=index"
        self.hostname = "rule34.xxx"
        self.limit = 1000
        self.retries = 3

    def _build_url_request(self, tag, page) -> str:
        return f"{self.base_url}{self.r34_api_string}&limit={self.limit}&tags={tag}&pid={page}"

    def get_board(self) -> BOARD:
        return BOARD.R34

    def get_posts(self, tag, post_limit=None) -> dict[str, Post]:
        posts = {}
        for page in range(10):
            response = requests.get(self._build_url_request(tag, page), timeout= 2.0)
            soup = BeautifulSoup(response.content, features="xml")
            # with open(f"output_{page}.html", 'w') as f:
            #     f.write(str(soup))
            raw_posts = soup.find_all("post")
            print(f"Request {page} - {len(raw_posts)}")
            for raw_post in raw_posts:
                post_id = str(raw_post["id"]).zfill(8)
                artist_name = tag
                tags=raw_post["tags"].split(" ")
                website = f'https://rule34.xxx/index.php?page=post&s=view&id={raw_post["id"]}'
                for black_listed in self.black_list:
                    if black_listed in tags:
                        stats.add(STATS.SKIP_COUNT, 1)
                        print(f"Skipping {post_id} for {black_listed}. ({website})")

                post = Post(
                    id=post_id,
                    artist_name=artist_name,
                    name=f"{post_id}-{artist_name}",
                    url=raw_post["file_url"],
                    tags=tags,
                    website = website,
                    board=BOARD.R34
                )
                stats.add(STATS.TAG_SET, artist_name)
                stats.add(STATS.TAG_SET, tags)
                stats.add(STATS.ARTIST_SET, artist_name)
                posts[post.id] = post
            if len(raw_posts) < self.limit:
                break
            time.sleep(0.5)
        stats.add(STATS.POST_COUNT, len(posts))
        return posts
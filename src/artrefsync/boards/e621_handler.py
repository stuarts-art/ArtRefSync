import requests
import base64
import json
import time
import artrefsync.stats as stats
from artrefsync.boards.board_handler import Post, ImageBoardHandler
from artrefsync.constants import STATS, BOARD, E621


class E621Handler(ImageBoardHandler):
    """Class to handle requesting and handling messages from the image board E621

    Args:
        ImageBoardHandler: Abstract Base Class which is implemented by the E621 Handler.
    """

    def __init__(self, config):
        username = config[E621.USERNAME]
        api_key = config[E621.API_KEY]
        self.website = "https://e621.net/posts.json"
        self.hostname = "e621.net"
        self.limit = 320
        user_string = f"{username}:{api_key}"
        self.website_headers = {
            "Authorization": f'Basic {base64.b64encode(user_string.encode("utf-8")).decode("utf-8")}',
            "User-Agent": f"MyProject/1.0 (by {username} on e621)",
        }

    def get_posts(self, tag, post_limit=None) -> dict[str, Post]:
        post_dict = {}
        post_list = self.get_raw_tag_data(tag)

        for raw_post in post_list:
            post = self.handle_post(raw_post, tag)
            post_dict[post.id] = post

        stats.add(STATS.POST_COUNT, (len(post_dict)))
        return post_dict

    def get_raw_tag_data(self, tag: str) -> list:
        print(f"Getting metadata for tag: {tag}")
        metadata = []
        oldest_id = ""
        for page in range(1, 50):  # handle pagination
            print(f"...getting page {page}")
            response = requests.get(
                self._build_website_parameters(page, tag),
                headers=self.website_headers,
                timeout=2,
            )
            page_data = json.loads(response.content)["posts"]
            print(len(page_data))
            if len(page_data) == 0:
                break

            if page != 1:
                if len(page_data) < self.limit or (oldest_id == page_data[-1]["id"]):
                    print("Repeat ID found. Ending.")
                    break
            oldest_id = page_data[-1]["id"]
            metadata.extend(page_data)
            time.sleep(1)
        return metadata

    def handle_post(self, post, artist):
        species = post["tags"]["species"]
        artists = post["tags"]["artist"]
        copyright = post["tags"]["copyright"]
        character = post["tags"]["character"]
        meta = post["tags"]["meta"]
        rating = f"rating_{post["rating"]}"
        tags = species + artists + copyright + character + meta + [rating]

        id = str(post["id"]).zfill(8)
        name = id + (
            (f"-{'_'.join(character)}" if character else "")
            + (f"-{'_'.join(species)}" if species else "")
        )

        url = post["file"]["url"]
        website = f"https://e621.net/posts/{post["id"]}"

        stats.add(STATS.TAG_SET, tags)
        stats.add(STATS.SPECIES_SET, species)
        stats.add(STATS.ARTIST_SET, artists)
        stats.add(STATS.COPYRIGHT_SET, copyright)
        stats.add(STATS.CHARACTER_SET, character)
        stats.add(STATS.META_SET, meta)
        stats.add(STATS.RATING_SET, rating)

        return Post(id, artist, name, url, tags, website, BOARD.E621)

    def _build_website_parameters(self, page, tag) -> str:
        return f"{self.website}?limit={self.limit}&tags={tag}&page={page}"
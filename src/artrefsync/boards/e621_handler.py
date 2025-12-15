import time
import base64
import json
import requests
from artrefsync.api.e621_client import E621_Client
from artrefsync.config import config
from artrefsync.stats import stats
from artrefsync.boards.board_handler import Post, ImageBoardHandler
from artrefsync.constants import STATS, BOARD, E621, TABLE

import logging
logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)



def main():
    print("Hello World")
    api_key = config[TABLE.E621][E621.API_KEY]
    user_name = config[TABLE.E621][E621.USERNAME]
    # client = E621_Client(user_name, api_key)
    posts = e621_handler.client.get_posts("")

    for p in posts:
        try:
            if p.tags:
                artist = p.tags.artist[0]
                characters = []
                # print(p.tags.character)
                print(p.tags.copyright)
                for character in p.tags.character:
                    character = character.split("(")[0]
                    characters.append(character)
                characters = "".join(characters).removesuffix("_")
                print(f"{str(p.id).zfill(8)}.{artist}-{characters}")
        except Exception as e:
            print(e)
            print(p)
            break




class __E621Handler(ImageBoardHandler):
    """Class to handle messages from the image board E621
    """
    def __init__(self):
        username = config[BOARD.E621][E621.USERNAME]
        api_key = config[BOARD.E621][E621.API_KEY]
        self.black_list = config[BOARD.E621][E621.BLACK_LIST]
        self.artist_list = list(set(config[BOARD.E621][E621.ARTISTS]))

        self.client = E621_Client(username, api_key)
        self.website = "https://e621.net/posts.json"
        self.hostname = "e621.net"
        self.limit = 320
        user_string = f"{username}:{api_key}"
        self.website_headers = {
            "Authorization": f'Basic {base64.b64encode(user_string.encode("utf-8")).decode("utf-8")}',
            "User-Agent": f"MyProject/1.0 (by {username} on e621)",
        }

    def get_board(self) -> BOARD:
        return BOARD.E621
    
    def get_artist_list(self):
        return self.artist_list

    def get_posts(self, tag, post_limit=None) -> dict[str, Post]:
        post_dict = {}
        post_list = self.get_raw_tag_data(tag)

        print(f"{self.get_board()} - {tag} - TOTAL POSTS: {len(post_list)}")
        for raw_post in post_list:
            post = self.handle_post(raw_post, tag)
            if post:
                post_dict[post.id] = post
                stats.add(STATS.POST_COUNT, 1)
            else:
                stats.add(STATS.SKIP_COUNT, 1)
        return post_dict

    def get_raw_tag_data(self, tag: str) -> list:
        print(f"{self.get_board()} - Getting metadata for tag: {tag}")
        metadata = []
        oldest_id = ""
        last_time = time.time()
        for page in range(1, 50):  # handle pagination
            print(f"{self.get_board()},{tag} - Getting page {page}. Total received: {len(metadata)}.")
            response = requests.get(
                self._build_website_parameters(page, tag),
                headers=self.website_headers,
                timeout=10,
            )
            page_data = json.loads(response.content)["posts"]
            if len(page_data) == 0:
                break

            if page != 1:
                if len(page_data) < self.limit or (oldest_id == page_data[-1]["id"]):
                    break
            oldest_id = page_data[-1]["id"]
            metadata.extend(page_data)
            # time.sleep(.6)
            curr_time = time.time() - last_time
            if curr_time < .6:
                time.sleep(.6-curr_time)

        return metadata

    def handle_post(self, post, artist):
        general = post["tags"]["general"]
        species = post["tags"]["species"]
        artists = post["tags"]["artist"]
        franchise = post["tags"]["copyright"]
        character = post["tags"]["character"]
        meta = post["tags"]["meta"]
        rating = f"rating_{post["rating"]}"
        tags = general + species + artists + franchise + character + meta + [rating]


        pid = Post.make_storage_id(post["id"], self.get_board())
        name = pid + (
            (f"-{'_'.join(franchise)}" if franchise else "")
            + (f"-{'_'.join(character)}" if character else "")
            + (f"-{'_'.join(species)}" if species else "")
        )

        url = post["file"]["url"]
        website = f"https://e621.net/posts/{post["id"]}"

        for black_listed in self.black_list:
            if black_listed in tags:
                # print(f"Skipping {pid} for {black_listed}. ({website})")
                stats.add(STATS.SKIP_COUNT)
                return None

        stats.add(STATS.TAG_SET, tags)
        stats.add(STATS.SPECIES_SET, species)
        stats.add(STATS.ARTIST_SET, artists)
        stats.add(STATS.COPYRIGHT_SET, franchise)
        stats.add(STATS.CHARACTER_SET, character)
        stats.add(STATS.META_SET, meta)
        stats.add(STATS.RATING_SET, rating)

        return Post(pid, artist, name, url, tags, website, BOARD.E621)

    def _build_website_parameters(self, page, tag) -> str:
        return f"{self.website}?limit={self.limit}&tags={tag}&page={page}"
    
    
e621_handler = __E621Handler()

if __name__ == "__main__":
    main()
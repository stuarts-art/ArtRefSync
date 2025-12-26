import time
import base64
import json
import requests
from artrefsync.api.e621_client import E621_Client
from artrefsync.config import config
from artrefsync.stats import stats
from artrefsync.boards.board_handler import Post, ImageBoardHandler
from artrefsync.constants import STATS, BOARD, E621, TABLE
from artrefsync.metadata_cache import metadata_cache

import logging
logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)

class __E621Handler(ImageBoardHandler):
    """Class to handle messages from the image board E621
    """
    def __init__(self):
        logger.info("Initialize E621 Handler")
        self.reload()
        config.subscribe_reload(self.reload)
    
    def reload(self):
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

    @metadata_cache
    def get_posts(self, tag, post_limit = None) -> dict[str, Post]:
        
        post_dict = {}
        e621_posts = self.client.get_posts(tag, post_limit)
        if ' ' in tag:
            tag = tag.split()[0] # Remove query and metatags

        for epost in e621_posts:
            tags = []
            general = epost.tags.general
            species = epost.tags.species
            artists = epost.tags.artist
            franchise = epost.tags.copyright
            character = epost.tags.character
            meta = epost.tags.meta
            rating = f"rating_{epost.rating}"
            tags = general + species + artists + franchise + character + meta + [rating]

            pid = Post.make_storage_id(epost.id, self.get_board())
            name = f"{pid}-{tag}"
            url = epost.file.url
            website = f"https://e621.net/posts/{epost.id}"
            post_id = Post.make_storage_id(epost.id, self.get_board())

            is_black_listed = False
            for black_listed in self.black_list:
                if black_listed in tags:
                    stats.add(STATS.SKIP_COUNT, 1)
                    logger.debug("Skipping %s for blacklist item '%s'. %s", post_id, black_listed, website)
                    is_black_listed = True
                    break
            if is_black_listed:
                continue

            
                    

            post = Post(
                id = pid,
                ext_id=epost.id,
                name = name,
                artist_name=tag,
                tags=tags,
                score=epost.score,
                url=url,
                website=website,
                board=self.get_board(),
                file=""
            )
            stats.add(STATS.TAG_SET, tags)
            stats.add(STATS.SPECIES_SET, species)
            stats.add(STATS.ARTIST_SET, artists)
            stats.add(STATS.COPYRIGHT_SET, franchise)
            stats.add(STATS.CHARACTER_SET, character)
            stats.add(STATS.META_SET, meta)
            stats.add(STATS.RATING_SET, rating)
            post_dict[pid] = post
            stats.add(STATS.POST_COUNT)
        return post_dict

e621_handler = __E621Handler()

if __name__=="__main__":
    posts = e621_handler.client.get_posts("yasmil")

    print(len(posts))

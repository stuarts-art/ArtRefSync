import base64
from collections import defaultdict
import logging
from threading import Event

from artrefsync.api.e621_client import E621_Client
from artrefsync.api.e621_model import E621_Post
from artrefsync.boards.board_handler import ImageBoardHandler, Post
from artrefsync.config import config
from artrefsync.constants import BOARD, E621, STATS
from artrefsync.stats import stats
import asyncio

logger = logging.getLogger(__name__)


def main():
    pass


class E621Handler(ImageBoardHandler):
    """Class to handle messages from the image board E621"""

    def __init__(self, only_recent=False, stop_event:Event = None):
        logger.info("Initialize E621 Handler")
        self.only_recent = only_recent
        self.type_tags = defaultdict(set)
        self.stop_event = stop_event
        self.reload()
        config.subscribe_reload(self.reload)


    def reload(self):
        username = config[BOARD.E621][E621.USERNAME]
        api_key = config[BOARD.E621][E621.API_KEY]
        self.black_list = config[BOARD.E621][E621.BLACK_LIST]
        self.artist_list = list(set(config[BOARD.E621][E621.ARTISTS]))

        self.client = E621_Client(username, api_key, self.only_recent, self.stop_event)
        self.website = "https://e621.net/posts.json"
        self.hostname = "e621.net"
        self.limit = 320
        user_string = f"{username}:{api_key}"
        self.website_headers = {
            "Authorization": f"Basic {base64.b64encode(user_string.encode('utf-8')).decode('utf-8')}",
            "User-Agent": f"MyProject/1.0 (by {username} on e621)",
        }

    def get_type_tags(self) -> dict[str, str]:
        return self.type_tags

    def get_board(self) -> BOARD:
        return BOARD.E621

    def get_artist_list(self):
        return self.artist_list

    def get_posts(
        self, tag, post_limit=10000
    ) -> dict[str, Post]:
        post_dict = {}
        e621_posts: list[E621_Post] = self.client.get_posts(tag, post_limit)
        if self.stop_event and self.stop_event.is_set():
            return None
        if " " in tag:
            tag = tag.split()[0]  # Remove query and metatags

        for e_post in e621_posts:
            tags = set()
            general = e_post.tags.general
            species = e_post.tags.species
            artists = e_post.tags.artist
            franchise = e_post.tags.copyright
            character = e_post.tags.character
            meta = e_post.tags.meta
            rating = f"rating_{e_post.rating.value}"
            pools = [f"pool_e621_{pool_id}" for pool_id in e_post.pools]
            ext = e_post.file.ext
            tags = ( []
                + general
                + species
                + artists
                + franchise
                + character
                + meta
                + [
                    rating,
                    e_post.file.ext,
                    tag,
                    BOARD.E621.value,
                ]
                + pools
            )
            try:
                created_datetime = e_post.created_at
                create_timestamp = int(created_datetime.timestamp())
                tags.append(str(created_datetime.year))
            except Exception:
                create_timestamp = 0

            try:
                updated_datetime = e_post.updated_at
                update_timestamp = int(updated_datetime.timestamp())
            except Exception:
                update_timestamp = 0

            pid = Post.make_storage_id(e_post.id, self.get_board())
            name = f"{pid}-{tag}"
            url = e_post.file.url
            website = f"https://e621.net/posts/{e_post.id}"
            post_id = Post.make_storage_id(e_post.id, self.get_board())

            is_black_listed = False
            for black_listed in self.black_list:
                if black_listed in tags:
                    stats.add(STATS.SKIP_COUNT, 1)
                    logger.debug(
                        "Skipping %s for blacklist item '%s'. %s",
                        post_id,
                        black_listed,
                        website,
                    )
                    is_black_listed = True
                    break
            if is_black_listed:
                continue

            # Add after blacklist
            self.type_tags["species"].update(e_post.tags.species)
            self.type_tags["artist"].update(e_post.tags.artist)
            self.type_tags["copyright"].update(e_post.tags.copyright)
            self.type_tags["character"].update(e_post.tags.character)
            self.type_tags["metadata"].update(e_post.tags.meta)
            self.type_tags["lore"].update(e_post.tags.lore)

            self.type_tags["artist"].add(str(tag))
            self.type_tags["rating"].add(str(rating))
            self.type_tags["format"].add(str(ext))
            self.type_tags["board"].add(str(self.get_board()))

            height = e_post.file.height
            width = e_post.file.width
            ratio = None
            if height and width:
                ratio = height / width
            post = Post(
                id=pid,
                ext_id=e_post.id,
                name=name,
                artist_name=tag,
                tags=list(dict.fromkeys(tags)),
                score=e_post.score.up,
                url=url,
                md5=e_post.file.md5,
                update_timestamp=update_timestamp,
                create_timestamp=create_timestamp,
                website=website,
                height=height,
                width=width,
                ratio=ratio,
                ext=e_post.file.ext,
                board=self.get_board(),
                file_link=e_post.file.url,
                sample_link=e_post.sample.url,
                preview_link=e_post.preview.url,
            )
            post_dict[pid] = post
        return post_dict


if __name__ == "__main__":
    main()

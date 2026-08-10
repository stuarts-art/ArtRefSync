import logging
from collections import defaultdict
from datetime import datetime
from threading import Event

from artrefsync.api.danbooru_client import Danbooru_Client
from artrefsync.boards.board_handler import ImageBoardHandler
from artrefsync.boards.board_models import Post
from artrefsync.config import get_config
from artrefsync.constants import BOARD, DANBOORU
from artrefsync.db.post_db import PostDb

config = get_config()
logger = logging.getLogger(__name__)


class DanbooruHandler(ImageBoardHandler):
    """
    Class to handle requesting and handling messages from the image board E621
    """

    def __init__(self, only_recent=False, stop_event: Event | None = None):
        self.only_recent = only_recent
        logger.info("Initialize Danbooru Handler")
        self.type_tags = defaultdict(set)
        self.stop_event = stop_event
        self.reload()
        config.subscribe_reload(self.reload)

    def reload(self):
        self.danbooru_api_key = config[BOARD.DANBOORU][DANBOORU.API_KEY]
        self.danbooru_username = config[BOARD.DANBOORU][DANBOORU.USERNAME]
        self.black_list = config[BOARD.DANBOORU][DANBOORU.BLACK_LIST]
        self.artist_list = list(set(config[BOARD.DANBOORU][DANBOORU.ARTISTS]))
        self.client = Danbooru_Client(
            self.danbooru_username,
            api_key=self.danbooru_api_key,
            only_recent=self.only_recent,
            stop_event=self.stop_event,
        )
        self.board = BOARD.DANBOORU

    def get_type_tags(self) -> dict[str, str]:
        return self.type_tags

    def get_artist_list(self):
        return self.artist_list

    def get_board(self) -> BOARD:
        return BOARD.DANBOORU

    def get_posts(self, tag, post_limit=None) -> dict[str, Post]:
        posts = {}

        last_id = None
        if self.only_recent:
            with PostDb() as post_db:
                row = post_db.posts.get(
                    board=self.get_board(),
                    artist_name=tag,
                    select_fields=["ext_id", "MAX(create_timestamp)"],
                    as_tuple=True,
                )
                if row:
                    last_id = row[0]
        danbooru_posts = self.client.get_posts(tag, post_limit, last_id=last_id)
        if self.stop_event and self.stop_event.is_set():
            return None
        if " " in tag:
            tag = tag.split()[0]  # Remove query and metatags
        logger.info("Recieved %s from client.", len(danbooru_posts))

        for d_post in danbooru_posts:
            website = f"https://danbooru.donmai.us/posts/{d_post.id}"
            post_id = Post.make_storage_id(d_post.id, self.get_board())
            is_black_listed = False
            tags = d_post.tag_string
            rating = f"rating_{d_post.rating}"
            ext = d_post.file_ext

            try:
                created_datetime = datetime.fromisoformat(d_post.created_at)
                create_timestamp = int(created_datetime.timestamp())
                tags.append(str(created_datetime.year))
            except Exception:
                create_timestamp = 0

            try:
                updated_datetime = datetime.fromisoformat(d_post.updated_at)
                update_timestamp = int(updated_datetime.timestamp())
            except Exception:
                update_timestamp = 0

            tags.append(rating)
            tags.append(f"{self.get_board().value}")
            tags.append(ext)
            tags.append(tag)

            for black_listed in self.black_list:
                if black_listed in tags:
                    logger.debug(
                        "Skipping %s for %s. (%s)", post_id, black_listed, website
                    )
                    is_black_listed = True
                    break
            if is_black_listed:
                continue

            self.type_tags["metadata"].update(d_post.tag_string_meta)
            self.type_tags["artist"].update(d_post.tag_string_artist)
            self.type_tags["character"].update(d_post.tag_string_character)
            self.type_tags["copyright"].update(d_post.tag_string_copyright)

            self.type_tags["artist"].add(str(tag))
            self.type_tags["rating"].add(str(rating))
            self.type_tags["format"].add(str(ext))
            self.type_tags["board"].add(str(self.get_board()))

            post = Post(
                id=post_id,
                ext_id=d_post.id,
                name=f"{post_id}-{tag}",
                artist_name=tag,
                tags=list(dict.fromkeys(tags)),
                board=self.board,
                md5=d_post.md5,
                update_timestamp=update_timestamp,
                create_timestamp=create_timestamp,
                score=d_post.score,
                url=d_post.file_url,
                website=website,
                height=d_post.image_height,
                width=d_post.image_width,
                ratio=(
                    d_post.image_width / d_post.image_height
                    if d_post.image_width and d_post.image_height
                    else None
                ),
                ext=d_post.file_ext,
                preview_link=d_post.preview_file_url,
                sample_link=d_post.large_file_url,
                file_link=d_post.file_url,
            )
            posts[post_id] = post
        return posts

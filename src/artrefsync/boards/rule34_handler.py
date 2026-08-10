import logging
from collections import defaultdict
from datetime import datetime
from threading import Event

from artrefsync.api.r34_client import R34_Client
from artrefsync.api.r34_model import R34_Post
from artrefsync.boards.board_handler import ImageBoardHandler
from artrefsync.boards.board_models import Post
from artrefsync.config import get_config

config = get_config()
from artrefsync.constants import BOARD, R34
from artrefsync.db.post_db import PostDb

logger = logging.getLogger(__name__)


class R34Handler(ImageBoardHandler):
    """
    Class to handle requesting and handling messages from the image board R34
    """

    def __init__(self, only_recent=False, stop_event: Event = None):
        self.only_recent = only_recent
        self.stop_event = stop_event
        logger.info("Initialize R34 Handler")
        self.reload()
        config.subscribe_reload(self.reload)

    def reload(self):
        self.r34_api_string = config[BOARD.R34][R34.API_KEY]
        self.black_list = config[BOARD.R34][R34.BLACK_LIST]
        self.artist_list = list(set(config[BOARD.R34][R34.ARTISTS]))
        self.client = R34_Client(
            api_string=self.r34_api_string,
            only_recent=self.only_recent,
            stop_event=self.stop_event,
        )
        self.board = BOARD.R34
        self.type_tags = defaultdict(set)

    def get_type_tags(self) -> dict[str, str]:
        return self.type_tags

    def get_artist_list(self):
        return self.artist_list

    def get_board(self) -> BOARD:
        return BOARD.R34

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

        r34_posts: list[R34_Post] = self.client.get_posts(
            tag, post_limit, last_id=last_id
        )
        if self.stop_event and self.stop_event.is_set():
            return None

        if " " in tag:
            tag = tag.split()[0]  # Remove query and metatags
        logger.debug("Recieved %s from client.", len(r34_posts))

        for rpost in r34_posts:
            skip_rpost = False
            website = f"https://rule34.xxx/index.php?page=post&s=view&id={rpost.id}"
            post_id = Post.make_storage_id(rpost.id, self.get_board())
            ext = rpost.file_url.split(".")[-1]

            tags = rpost.tags + [tag, BOARD.R34.value, ext]
            rating = f"rating_{rpost.rating}"
            tags.append(rating)
            for black_listed in self.black_list:
                if black_listed in rpost.tags:
                    logger.debug(f"Skipping {post_id} for {black_listed}. ({website})")
                    skip_rpost = True
                    break
            if skip_rpost:
                continue

            for info in rpost.tag_info:
                if info.type == "tag":
                    continue
                self.type_tags[info.type].add(info.tag)
            self.type_tags["artist"].add(tag)
            self.type_tags["rating"].add(str(rating))
            self.type_tags["format"].add(str(ext))
            self.type_tags["board"].add(str(self.get_board()))

            try:
                created_datetime = datetime.strptime(
                    rpost.created_at, "%a %b %d %H:%M:%S %z %Y"
                )
                create_timestamp = int(created_datetime.timestamp())
                tags.append(str(created_datetime.year))
            except Exception:
                create_timestamp = 0

            try:
                updated_datetime = datetime.fromtimestamp(rpost.change)
                update_timestamp = int(updated_datetime.timestamp())
                if created_datetime == 0:
                    create_timestamp = update_timestamp
            except Exception:
                update_timestamp = 0

            post = Post(
                id=post_id,
                ext_id=rpost.id,
                name=f"{post_id}-{tag}",
                artist_name=tag,
                tags=list(dict.fromkeys(tags)),
                board=self.board,
                score=rpost.score,
                url=rpost.file_url,
                website=website,
                md5=rpost.hash,
                update_timestamp=update_timestamp,
                create_timestamp=create_timestamp,
                height=rpost.height,
                width=rpost.width,
                ratio=(
                    rpost.width / rpost.height if rpost.width and rpost.height else None
                ),
                sample_link=rpost.sample_url,
                preview_link=rpost.preview_url,
                file_link=rpost.file_url,
                ext=ext,
            )
            posts[post_id] = post

        logger.info("Returning %d posts for artist %s", len(posts), tag)
        return posts

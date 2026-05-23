from collections import defaultdict
import logging
from datetime import datetime
from threading import Event

from artrefsync.api.danbooru_client import Danbooru_Client
from artrefsync.boards.board_handler import ImageBoardHandler, Post
from artrefsync.config import config
from artrefsync.constants import BOARD, DANBOORU, STATS
from artrefsync.stats import stats

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


def main():
    pass


class Danbooru_Handler(ImageBoardHandler):
    """
    Class to handle requesting and handling messages from the image board E621
    """

    def __init__(self, only_recent=False):
        self.only_recent = only_recent
        logger.info("Initialize Danbooru Handler")
        self.reload()
        config.subscribe_reload(self.reload)
        self.type_tags = defaultdict(set)

    def reload(self):
        self.danbooru_api_key = config[BOARD.DANBOORU][DANBOORU.API_KEY]
        self.danbooru_username = config[BOARD.DANBOORU][DANBOORU.USERNAME]
        self.black_list = config[BOARD.DANBOORU][DANBOORU.BLACK_LIST]
        self.artist_list = list(set(config[BOARD.DANBOORU][DANBOORU.ARTISTS]))
        self.client = Danbooru_Client(
            self.danbooru_username,
            api_key=self.danbooru_api_key,
            only_recent=self.only_recent,
        )
        self.board = BOARD.DANBOORU

    def get_type_tags(self) -> dict[str, str]:
        return self.type_tags

    def get_artist_list(self):
        return self.artist_list

    def get_board(self) -> BOARD:
        return BOARD.DANBOORU

    # @disk_cache
    def get_posts(
        self, tag, post_limit=None, stop_event: Event = None
    ) -> dict[str, Post]:
        posts = {}

        danbooru_posts = self.client.get_posts(tag, post_limit)
        if stop_event and stop_event.is_set():
            return None
        if " " in tag:
            tag = tag.split()[0]  # Remove query and metatags
        logger.info("Recieved %s from client.", len(danbooru_posts))

        for dpost in danbooru_posts:
            website = f"https://danbooru.donmai.us/posts/{dpost.id}"
            post_id = Post.make_storage_id(dpost.id, self.get_board())
            is_black_listed = False
            tags = dpost.tag_string
            rating = "rating_{dpost.rating}"
            ext = dpost.file_ext

            try:
                created_datetime = datetime.fromisoformat(dpost.created_at)
                create_timestamp = int(created_datetime.timestamp())
                tags.append(str(created_datetime.year))
            except Exception:
                create_timestamp = 0

            try:
                updated_datetime = datetime.fromisoformat(dpost.updated_at)
                update_timestamp = int(updated_datetime.timestamp())
            except Exception:
                update_timestamp = 0

            tags.append(rating)
            tags.append(f"{self.get_board().value}")
            tags.append(ext)
            tags.append(tag)

            for black_listed in self.black_list:
                if black_listed in tags:
                    stats.add(STATS.SKIP_COUNT, 1)
                    logger.debug(
                        "Skipping %s for %s. (%s)", post_id, black_listed, website
                    )
                    is_black_listed = True
                    break
            if is_black_listed:
                continue


            self.type_tags["metadata"].update(dpost.tag_string_meta)
            self.type_tags["artist"].update(dpost.tag_string_artist)
            self.type_tags["character"].update(dpost.tag_string_character)
            self.type_tags["copyright"].update(dpost.tag_string_copyright)

            self.type_tags["artist"].add(str(tag))
            self.type_tags["rating"].add(str(rating))
            self.type_tags["format"].add(str(ext))
            self.type_tags["board"].add(str(self.get_board()))

            post = Post(
                id=post_id,
                ext_id=dpost.id,
                name=f"{post_id}-{tag}",
                artist_name=tag,
                tags=list(dict.fromkeys(tags)),
                board=self.board,
                md5=dpost.md5,
                update_timestamp=update_timestamp,
                create_timestamp=create_timestamp,
                score=dpost.score,
                url=dpost.file_url,
                website=website,
                height=dpost.image_height,
                width=dpost.image_width,
                ratio=(
                    dpost.image_width / dpost.image_height
                    if dpost.image_width and dpost.image_height
                    else None
                ),
                ext=dpost.file_ext,
                preview_link=dpost.preview_file_url,
                sample_link=dpost.large_file_url,
                file_link=dpost.file_url,
            )
            stats.add(STATS.TAG_SET, dpost.tag_string)
            stats.add(STATS.TAG_SET, tag)
            stats.add(STATS.ARTIST_SET, tag)
            posts[post_id] = post
            stats.add(STATS.POST_COUNT)
        return posts


if __name__ == "__main__":
    main()

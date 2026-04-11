import concurrent
import logging
from asyncio import Event
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from artrefsync.boards.board_handler import ImageBoardHandler, Post, PostFile
from artrefsync.boards.danbooru_handler import Danbooru_Handler
from artrefsync.boards.e621_handler import E621Handler
from artrefsync.boards.rule34_handler import R34Handler
from artrefsync.config import config
from artrefsync.constants import (
    APP,
    BINDING,
    BOARD,
    DANBOORU,
    E621,
    EAGLE,
    LOCAL,
    R34,
    TABLE,
)
from artrefsync.db.post_db import PostDb
from artrefsync.stores.eagle_storage import EagleHandler
from artrefsync.stores.link_cache import LinkCache
from artrefsync.stores.plain_file_storage import PlainLocalStorage
from artrefsync.stores.storage import ImageStoreHandler
from artrefsync.utils.EventManager import ebinder

logger = logging.getLogger(__name__)


def main():
    coordinator = SyncCoordinator(E621Handler(), EagleHandler())
    coordinator.sync()


def sync_config(event: Event):
    try:
        limit = int(config[TABLE.APP][APP.LIMIT])
        store = None
        if config[TABLE.EAGLE][EAGLE.ENABLED]:
            store = EagleHandler()
        elif config[TABLE.LOCAL][LOCAL.ENABLED]:
            store = PlainLocalStorage()

        only_recent = config[TABLE.APP][APP.ONLY_RECENT_ENABLED]

        # EAGLE Overrides the normal FS storage.

        if store is None:
            logger.warning("NO STORE ENABLED. ENDING SYNC")
            return

        if config[TABLE.E621][E621.ENABLED] and not event.is_set():
            logger.info("Syncing %s with store: %s", TABLE.E621, store.get_store())
            board = E621Handler(only_recent)
            sync(board, store, limit, event)

        if config[TABLE.R34][R34.ENABLED] and not event.is_set():
            logger.info("Syncing %s with store: %s", TABLE.R34, store.get_store())
            board = R34Handler(only_recent)
            sync(board, store, limit, event)

        if config[TABLE.DANBOORU][DANBOORU.ENABLED] and not event.is_set():
            logger.info("Syncing %s with store: %s", TABLE.DANBOORU, store.get_store())
            board = Danbooru_Handler(only_recent)
            sync(board, store, limit, event)
    finally:
        ebinder.event_generate(BINDING.ON_LOADING_DONE)


def sync_from_store(event: Event):
    try:
        store = None
        if config[TABLE.EAGLE][EAGLE.ENABLED]:
            store = EagleHandler()
        elif config[TABLE.LOCAL][LOCAL.ENABLED]:
            store = PlainLocalStorage()
        if store is None:
            logger.warning("NO STORE ENABLED. ENDING SYNC")
            return

        for board in BOARD:
            match board:
                case BOARD.R34:
                    handler = R34Handler()
                case BOARD.E621:
                    handler = E621Handler()
                case BOARD.DANBOORU:
                    handler = Danbooru_Handler()
                case _:
                    continue
            logger.info(
                "Updating File Table for Board %s, Store %s",
                handler.get_board(),
                store.get_store(),
            )
            sync_coordinator = SyncCoordinator(handler, store)
            for artist in handler.artist_list:
                if event.is_set():
                    return
                updated = sync_coordinator.update_post_file_table(artist=artist)
                logger.debug(
                    "%s, %s, %s, %d",
                    handler.get_board(),
                    store.get_store(),
                    artist,
                    len(updated),
                )
            sync_coordinator.update_board_tag_count(board, handler.artist_list)

    except Exception as e:
        logger.warning(e)


# TODO: Remove old Sync file
def sync(
    board: ImageBoardHandler,
    store: ImageStoreHandler,
    max_per_artist=10000,
    event: Event = Event(),
):
    logger.info(
        "Syncing %s to %s", board.get_board(), ", ".join(board.get_artist_list())
    )
    coordiantor = SyncCoordinator(board, store, max_per_artist, event)
    coordiantor.sync()


class SyncCoordinator:
    def __init__(
        self,
        board_handler: ImageBoardHandler,
        store_handler: ImageStoreHandler,
        max_per_artist: int = int(config[TABLE.APP][APP.LIMIT]),
        stop_event: Event = Event(),
    ):
        self.board_handler = board_handler
        self.store_handler = store_handler
        self.max_per_artist = max_per_artist
        self.stop_event = stop_event
        self.store = store_handler.get_store()
        self.board = board_handler.get_board()
        self.tag_post_dict = defaultdict(set)
        self.board_tag_counts = defaultdict(int)
        self.cache = LinkCache()
        self.download_count = 0
        self.max_download_threads = int(config[TABLE.APP][APP.MAX_DOWNLOAD_THREADS])

    def sync(self):
        ebinder.event_generate(
            BINDING.ON_LOAD_LEFT_SET, len(self.board_handler.artist_list)
        )
        for artist in self.board_handler.artist_list:
            if self.stop_event.is_set():
                return
            ebinder.event_generate(BINDING.ON_LOAD_LEFT_INCR, f"{self.board}: {artist}")
            self.sync_artist(artist)

        with PostDb() as post_db:
            ebinder.event_generate(BINDING.ON_LOAD_MID_SET, "Updating Tag table.")
            post_db.artist_tags.dumps_blob(str(self.board), self.board_tag_counts)
            for tag, posts in self.tag_post_dict.items():
                if self.stop_event.is_set():
                    return
                post_db.tag_posts.union_update(tag, posts)

    def sync_artist(self, artist):
        logger.info("Starting sync artist %s", artist)
        self.update_metadata(artist)
        self.update_post_file_table(artist)
        self.download_missing_ids(artist)
        self.update_post_file_table(artist=artist)
        logger.debug("Ending sync artist %s", artist)

    def update_metadata(self, artist) -> list[Post]:
        logger.debug("Updating metadata for artist: %s", artist)
        ebinder.event_generate(BINDING.ON_LOAD_MID_SET, "Updating metadata")

        updated_posts = []
        artist_tag_count = defaultdict(int)
        posts: dict[str, Post] = self.board_handler.get_posts(
            artist, self.max_per_artist, self.stop_event
        )
        logger.info(
            "Recieved %d metadata posts for %s from board %s",
            len(posts) if posts else 0,
            artist,
            self.board,
        )
        with PostDb() as post_db:
            for pid, post in posts.items():
                inserted = post_db.posts.insert(post)
                if inserted:
                    updated_posts.append(post)
                post.tags.append(post.ext)
                post.tags.append(post.artist_name)
                for tag in post.tags:
                    self.tag_post_dict[tag].add(pid)
                    self.board_tag_counts[tag] += 1
                    artist_tag_count[tag] += 1
            post_db.artist_tags.dumps_blob(artist, artist_tag_count)
            post_db.artist_tags.commit()
        logger.info(
            "Updated %d metadata posts for %s from board %s",
            len(updated_posts) if updated_posts else 0,
            artist,
            self.board,
        )
        return updated_posts

    def get_missing_ids(self, artist: str):
        missing_ids = []
        storeposts = self.store_handler.get_posts(self.board, artist)
        logger.info("%d store posts for %s", len(storeposts), artist)
        with PostDb() as post_db:
            post_ids = post_db.posts.select_id_list(
                [("artist_name", artist), ("board", self.board)]
            )

            for pid in post_ids:
                if pid not in storeposts:
                    # if pid not in storeposts or pid not in post_file_ids:
                    missing_ids.append(pid)
                else:
                    if not storeposts[pid].thumbnail or not storeposts[pid].sample:
                        missing_ids.append(pid)
            return missing_ids

    def update_board_tag_count(self, board, artists):
        board_tags_count = defaultdict(int)

        with PostDb() as post_db:
            for artist in artists:
                artist_tags_count = self.update_artist_tag_tables(board, artist)
                if artist_tags_count:
                    for tag, count in artist_tags_count.items:
                        board_tags_count[tag] += count
            post_db.artist_tags.dumps_blob(str(board), board_tags_count)

    def update_artist_tag_tables(self, board, artist):
        board = str(board)
        artist_tag_counts = defaultdict(set)
        tag_posts = defaultdict(set)
        with PostDb() as post_db:
            posts = post_db.posts.select(
                conditions=[("artist_name", artist), ("board", board)],
                select_fields=["id", "tags", "ext"],
            )
            for post in posts:
                pid = post["id"]
                ext = post["ext"]
                tags = set(post["tags"] + [board, artist, ext])

                for tag in tags:
                    artist_tag_counts[tag] += 1
                    tag_posts[tag].add(pid)
            for tag, posts in tag_posts.items():
                post_db.tag_posts.union_update(tag, posts)
        return artist_tag_counts

    def download_missing_ids(self, artist):
        ebinder.event_generate(BINDING.ON_LOAD_MID_SET, "Downloading missing")

        missing_ids = self.get_missing_ids(artist)
        failure_list = []
        success_list = []
        if not missing_ids:
            return []
        with PostDb() as post_db:
            missing_posts = [post_db.posts[id] for id in missing_ids]
        if not missing_posts:
            return

        logger.info("Downloading %d missing posts for %s", len(missing_posts), artist)

        # thread_caller = TkThreadCaller()
        with ThreadPoolExecutor(max_workers=self.max_download_threads) as executor:
            future_to_pid = {}
            for post in missing_posts:
                future = executor.submit(
                    self.store_handler.save_post,
                    post=post,
                    link_cache=self.cache,
                    event=self.stop_event,
                )
                future_to_pid[future] = post.id
            ebinder.event_generate(
                BINDING.ON_LOAD_RIGHT_SET, len(missing_posts), "Downloading: "
            )
            for future in concurrent.futures.as_completed(future_to_pid.keys()):
                try:
                    result = future.result()
                    ebinder.event_generate(BINDING.ON_LOAD_RIGHT_INCR)
                    if self.stop_event and self.stop_event.is_set():
                        logger.warning("Stop Event Recieved.")
                        executor.shutdown(wait=True, cancel_futures=True)
                        return
                    if isinstance(result, PostFile):
                        success_list.append(result)
                except Exception as e:
                    logger.error(e)

                    failure_list.append(future_to_pid[future])
                    # continue
            if failure_list:
                logger.error("The following IDs failed to load. %s", failure_list)

        logger.info("Adding Entries to PostFile Table.")
        with PostDb() as post_db:
            for post_file in success_list:
                post_db.files.insert(post_file)

        return success_list

    def update_post_file_table(self, artist, repair=False):
        ebinder.event_generate(BINDING.ON_LOAD_MID_SET, "Updating PostFile table")
        logger.info(
            "Updating PostFile Table for %s, %s, %s", self.store, self.board, artist
        )
        store_posts: dict[str, PostFile] = self.store_handler.get_posts(
            self.board, artist
        )
        logger.info("store_posts recieved with %s records.", len(store_posts))
        inserted_list = []

        with PostDb() as post_db:
            metadata_ids = post_db.posts.select_id_list(
                [("board", str(self.board)), ("artist_name", artist)]
            )
            for pid, store_post in store_posts.items():
                if pid not in metadata_ids:
                    continue
                post = post_db.posts[pid]

                if pid in post_db.files:
                    old_file: PostFile = post_db.files[pid]
                    if (
                        old_file.file == store_post.file
                        and old_file.sample == store_post.sample
                        and old_file.preview == store_post.preview
                        and old_file.thumbnail == store_post.thumbnail
                    ):
                        continue
                inserted = None

                if pid in store_posts:
                    store_post = store_posts[pid]
                    post = post_db.posts[pid]
                    post_file = PostFile(
                        id=post.id,
                        ext_id=store_post.ext_id,
                        store=store_post.store,
                        board=post.board,
                        artist_name=post.artist_name,
                        height=post.height,
                        width=post.width,
                        ratio=post.ratio,
                        ext=post.ext,
                        preview=store_post.preview,
                        thumbnail=store_post.thumbnail,
                        sample=store_post.sample,
                        file=store_post.file,
                    )
                    inserted = post_db.files.insert(post_file)
                if inserted:
                    inserted_list.append(pid)
        logger.info(
            "Inserted %d PostFile Table for %s, %s, %s",
            len(inserted_list),
            self.store,
            self.board,
            artist,
        )
        return inserted_list


if __name__ == "__main__":
    main()

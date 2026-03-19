from asyncio import Event
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import concurrent
import logging
import time

from artrefsync.boards.danbooru_handler import Danbooru_Handler
from artrefsync.boards.rule34_handler import R34Handler
from artrefsync.boards.e621_handler import E621Handler
from artrefsync.boards.board_handler import ImageBoardHandler, Post, PostFile
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
from artrefsync.stores.plain_file_storage import PlainLocalStorage
from artrefsync.stores.storage import ImageStoreHandler
from artrefsync.stores.eagle_storage import EagleHandler
from artrefsync.config import config
from artrefsync.stores.link_cache import Link_Cache
from artrefsync.utils.EventManager import ebinder

logger = logging.getLogger(__name__)


def main():
    event = Event()
    sync_config(event)


def sync_config(event: Event):
    try:
        limit = int(config[TABLE.APP][APP.LIMIT])
        store = None
        if config[TABLE.EAGLE][EAGLE.ENABLED]:
            store = EagleHandler()
        elif config[TABLE.LOCAL][LOCAL.ENABLED]:
            store = PlainLocalStorage()

        # EAGLE Overrides the normal FS storage.

        if store is None:
            logger.warning("NO STORE ENABLED. ENDING SYNC")
            return

        if config[TABLE.E621][E621.ENABLED] and not event.is_set():
            logger.info("Syncing %s with store: %s", TABLE.E621, store.get_store())
            board = E621Handler()
            sync(board, store, limit, event)

        if config[TABLE.R34][R34.ENABLED] and not event.is_set():
            logger.info("Syncing %s with store: %s", TABLE.R34, store.get_store())
            board = R34Handler()
            sync(board, store, limit, event)

        if config[TABLE.DANBOORU][DANBOORU.ENABLED] and not event.is_set():
            logger.info("Syncing %s with store: %s", TABLE.DANBOORU, store.get_store())
            board = Danbooru_Handler()
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
        max_per_artist: int = None,
        stop_event: Event = None,
    ):
        self.board_handler = board_handler
        self.store_handler = store_handler
        self.max_per_artist = max_per_artist
        self.stop_event = stop_event
        self.store = store_handler.get_store()
        self.board = board_handler.get_board()
        self.tag_post_dict = defaultdict(set)
        self.board_tag_count = defaultdict(int)
        self.cache = Link_Cache()
        self.download_count = 0

    def sync(self):
        ebinder.event_generate(
            BINDING.ON_LOAD_LEFT_SET, len(self.board_handler.artist_list)
        )
        for artist in self.board_handler.artist_list:
            if self.stop_event.is_set():
                return
            ebinder.event_generate(BINDING.ON_LOAD_LEFT_INCR, f"{self.board}: {artist}")
            self.sync_artist(artist)
            self.update_post_file_table(artist)

        with PostDb() as post_db:
            post_db.artist_tags.dumps_blob(str(self.board), self.board_tag_count)
            for tag, posts in self.tag_post_dict.items():
                if self.stop_event.is_set():
                    return
                post_db.tag_posts.union_update(tag, posts)

        for artist in self.board_handler.artist_list:
            if self.stop_event.is_set():
                return
            self.store_handler.update_thumbnails(self.board, artist)

    def sync_artist(self, artist):
        logger.info("Starting sync artist %s", artist)
        self.update_metadata(artist)
        self.update_post_file_table(artist)
        download_list = self.download_missing_ids(artist)

        for retry in range(1, 4):
            inserted_post_files = self.update_post_file_table(artist)
            download_list = [
                pid for pid in download_list if pid not in inserted_post_files
            ]
            if not download_list:
                break
            logger.debug(
                "Waiting for %d files to sync for artist %s", len(download_list), artist
            )
            time.sleep(0.5 * retry)
        logger.debug("Ending sync artist %s", artist)

    def update_metadata(self, artist) -> list[Post]:
        logger.debug("Updating metadata for artist: %s", artist)

        updated_posts = []
        artist_tag_count = defaultdict(int)
        posts: dict[str, Post] = self.board_handler.get_posts(
            artist, self.max_per_artist, self.stop_event
        )
        logger.debug(
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
                    self.board_tag_count[tag] += 1
                    artist_tag_count[tag] += 1
            post_db.artist_tags.dumps_blob(artist, artist_tag_count)
            post_db.artist_tags.commit()
        logger.debug(
            "Updated %d metadata posts for %s from board %s",
            len(updated_posts) if updated_posts else 0,
            artist,
            self.board,
        )
        return updated_posts

    def get_missing_ids(self, artist: str):
        with PostDb() as post_db:
            post_ids = post_db.posts.select_id_list(
                [("artist_name", artist), ("board", self.board)]
            )
            post_file_ids = post_db.files.select_id_list(
                [("artist_name", artist), ("board", self.board)]
            )
            missing_ids = [
                post_id for post_id in post_ids if post_id not in post_file_ids
            ]
            return missing_ids

    def download_missing_ids(self, artist):
        missing_ids = self.get_missing_ids(artist)
        if not missing_ids:
            return []

        with PostDb() as post_db:
            missing_posts = [post_db.posts[id] for id in missing_ids]

        with ThreadPoolExecutor() as executor:
            future_to_pid = {
                executor.submit(
                    self.store_handler.save_post, post, self.cache, self.stop_event
                ): post.id
                for post in missing_posts
            }
            failure_list = []
            success_list = []
            ebinder.event_generate(
                BINDING.ON_LOAD_RIGHT_SET, len(missing_posts), "Downloading: "
            )
            for future in concurrent.futures.as_completed(future_to_pid.keys()):
                try:
                    ebinder.event_generate(BINDING.ON_LOAD_RIGHT_INCR)
                    result = future.result()
                    success_list.append(future_to_pid[future])
                    if self.stop_event and self.stop_event.is_set():
                        logger.warning("Stop Event Recieved.")
                        executor.shutdown(wait=True, cancel_futures=True)
                        return
                except Exception as e:
                    failure_list.append(future_to_pid[future])
                    continue

        self.download_count += 1
        if failure_list:
            logger.error("The following IDs failed to load. %s", failure_list)

        return success_list

    def update_post_file_table(self, artist, repair=False):
        logger.debug(
            "Updating PostFile Table for %s, %s, %s", self.store, self.board, artist
        )
        store_posts: dict[str, PostFile] = self.store_handler.get_posts(
            self.board, artist
        )
        logger.debug("store_posts recieved with %s records.", len(store_posts))
        inserted_list = []
        with PostDb() as post_db:
            metadata_ids = post_db.posts.select_id_list(
                [("board", self.board), ("artist_name", artist)]
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
        logger.debug(
            "Inserted %d PostFile Table for %s, %s, %s",
            len(inserted_list),
            self.store,
            self.board,
            artist,
        )
        return inserted_list


if __name__ == "__main__":
    main()

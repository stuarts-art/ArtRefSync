import concurrent
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock

from artrefsync.boards.board_models import Post
from artrefsync.stores.store_models import PostFile
from artrefsync.boards.board_handler import ImageBoardHandler
from artrefsync.boards.danbooru_handler import DanbooruHandler
from artrefsync.boards.e621_handler import E621Handler
from artrefsync.boards.rule34_handler import R34Handler
from artrefsync.config import get_config
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
from artrefsync.db.db_models import ArtistTagCount
from artrefsync.stores.eagle_storage import EagleHandler
from artrefsync.stores.link_cache import LinkCache
from artrefsync.stores.plain_file_storage import PlainLocalStorage
from artrefsync.stores.storage import ImageStoreHandler
from artrefsync.utils.EventManager import e_binder

config = get_config()
logger = logging.getLogger(__name__)


def sync_config(event: Event):
    try:
        limit = int(config[TABLE.APP][APP.LIMIT])
        store = None
        if config[TABLE.EAGLE][EAGLE.ENABLED]:
            store = EagleHandler()
        elif config[TABLE.LOCAL][LOCAL.ENABLED]:
            store = PlainLocalStorage()

        only_recent = config[TABLE.APP][APP.ONLY_RECENT_ENABLED]

        if store is None:
            logger.warning("NO STORE ENABLED. ENDING SYNC")
            return

        if config[TABLE.E621][E621.ENABLED] and not event.is_set():
            logger.info("Syncing %s with store: %s", TABLE.E621, store.get_store())
            board = E621Handler(only_recent, event)
            sync(board, store, limit, event)

        if config[TABLE.R34][R34.ENABLED] and not event.is_set():
            logger.info("Syncing %s with store: %s", TABLE.R34, store.get_store())
            board = R34Handler(only_recent, event)
            sync(board, store, limit, event)

        if config[TABLE.DANBOORU][DANBOORU.ENABLED] and not event.is_set():
            logger.info("Syncing %s with store: %s", TABLE.DANBOORU, store.get_store())
            board = DanbooruHandler(only_recent, event)
            sync(board, store, limit, event)
    finally:
        e_binder.event_generate(BINDING.ON_LOADING_DONE)


def sync_artist(artist_name: str, board_name: str | BOARD, stop_event: Event | None = None, only_recent = False, limit: int | None = None):
    try:
        if not board_name:
            logger.error("No board name provided")
            return
        elif not artist_name:
            logger.error("No artist name provided")
            return
        board = BOARD(board_name)
        match board:
            case BOARD.E621:
                board_handler = E621Handler(only_recent=only_recent)
            case BOARD.DANBOORU:
                board_handler = DanbooruHandler(only_recent=only_recent)
            case BOARD.R34:
                board_handler = R34Handler(only_recent=only_recent)
        if limit is None:
            limit = int(config[TABLE.APP][APP.LIMIT])
        if config[TABLE.EAGLE][EAGLE.ENABLED]:
            store_handler = EagleHandler()
        elif config[TABLE.LOCAL][LOCAL.ENABLED]:
            store_handler = PlainLocalStorage()

        sync_coordinator = SyncCoordinator(
            board_handler=board_handler, store_handler=store_handler, max_per_artist=limit
        )
        sync_coordinator.sync([artist_name])
    finally:
        e_binder.event_generate(BINDING.ON_ARTIST_SYNC_DONE)


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
                    handler = DanbooruHandler()
                case _:
                    continue
            logger.info(
                "Updating File Table for Board %s, Store %s",
                handler.get_board(),
                store.get_store(),
            )
            sync_coordinator = SyncCoordinator(handler, store)
            sync_coordinator.update_metadata(handler.artist_list)

    except Exception:
        logger.exception("Failed to sync from store.")


def sync(
    board: ImageBoardHandler,
    store: ImageStoreHandler,
    max_per_artist=10000,
    event: Event | None = None,
):
    logger.info(
        "Syncing %s to %s", board.get_board(), ", ".join(board.get_artist_list())
    )
    coordinator = SyncCoordinator(board, store, max_per_artist, event)
    coordinator.sync()


class SyncCoordinator:
    def __init__(
        self,
        board_handler: ImageBoardHandler,
        store_handler: ImageStoreHandler,
        max_per_artist: int | None = None,
        stop_event: Event | None = None,
    ):
        self.board_handler = board_handler
        self.store_handler = store_handler
        if max_per_artist is None:
            self.max_per_artist = int(config[TABLE.APP][APP.LIMIT])
        else:
            self.max_per_artist = max_per_artist
        self.stop_event: Event | None = stop_event
        self.store = store_handler.get_store()
        self.board = board_handler.get_board()
        self.tag_post_dict = defaultdict(set)
        self.board_tag_counts = defaultdict(int)
        self.cache = LinkCache()
        self.download_count = 0
        self.max_download_threads = int(config[TABLE.APP][APP.MAX_DOWNLOAD_THREADS])
        self.artist_list = self.board_handler.get_artist_list()

    def sync(self, artist_list: None | list[str] = None):
        try:
            if artist_list:
                self.artist_list = artist_list
            else:
                self.artist_list = self.board_handler.get_artist_list()
            self.sync_artist_metadata(self.artist_list)
            e_binder.event_generate(BINDING.ON_LOAD_LEFT_SET, len(self.artist_list))
            for artist in self.artist_list:
                if self.stop_event and self.stop_event.is_set():
                    return
                e_binder.event_generate(
                    BINDING.ON_LOAD_LEFT_INCR, f"{self.board}: {artist}"
                )
                self.sync_artist_files(artist)

            e_binder.event_generate(BINDING.ON_LOAD_MID_SET, "Updating Tag table.")
            self.update_board_artist_tag_counts(self.board, self.artist_list)
        except Exception:
            logger.exception("Sync Failed.")

    def sync_artist_metadata(self, artists: list[str]):
        e_binder.event_generate(BINDING.ON_LOAD_LEFT_SET, len(self.artist_list))
        logger.info("Syncing artists: %s", artists)
        for artist in artists:
            e_binder.event_generate(
                BINDING.ON_LOAD_LEFT_INCR, f"{self.board}: {artist}"
            )
            e_binder.event_generate(BINDING.ON_LOAD_MID_SET, "Updating metadata")
            if self.stop_event and self.stop_event.is_set():
                return
            self.update_metadata(artist)
        self.update_tag_types()

    def sync_artist_files(self, artist):
        logger.info("Starting sync artist %s", artist)

        self.update_post_file_table(artist)
        self.download_missing_ids(artist)
        self.update_post_file_table(artist=artist)
        logger.debug("Ending sync artist %s", artist)

    def update_metadata(self, artist) -> list[Post]:
        logger.debug("Updating metadata for artist: %s", artist)
        e_binder.event_generate(BINDING.ON_LOAD_MID_SET, "Updating metadata")
        updated_posts = []
        board_posts: dict[str, Post] = self.board_handler.get_posts(
            artist, self.max_per_artist
        )
        logger.info(
            "Received %d metadata posts for %s from board %s",
            len(board_posts) if board_posts else 0,
            artist,
            self.board,
        )

        for board_post in board_posts.values():
            board_post.tags.append(board_post.ext)
            board_post.tags.append(board_post.ext)
            board_post.tags.append(board_post.artist_name)
            board_post.tags = list(dict.fromkeys(board_post.tags))

        with PostDb() as post_db:
            for board_post in board_posts.values():
                inserted = post_db.posts.insert(board_post)
                if inserted:
                    post_db.update_tag_link_table(inserted, board_post.tags)
                    updated_posts.append(board_post)

        logger.info(
            "Updated %d metadata posts for %s from board %s",
            len(updated_posts) if updated_posts else 0,
            artist,
            self.board,
        )
        return updated_posts

    def get_missing_ids(self, artist: str):
        missing_ids = []
        store_posts = self.store_handler.get_posts(self.board, artist)
        logger.info("%d store posts for %s", len(store_posts), artist)

        with PostDb() as post_db:
            post_ids = post_db.posts.get_all(
                artist_name=artist,
                board=self.board,
                select_fields=["id"],
                as_tuple=True,
            )
            post_ids = [row[0] for row in post_ids]

            for pid in post_ids:
                if pid not in store_posts:
                    missing_ids.append(pid)
                else:
                    if not store_posts[pid].thumbnail or not store_posts[pid].sample:
                        missing_ids.append(pid)
            return missing_ids

    def download_missing_ids(self, artist):
        e_binder.event_generate(BINDING.ON_LOAD_MID_SET, "Downloading missing")

        missing_ids = self.get_missing_ids(artist)
        failure_list = []
        success_list: list[PostFile] = []
        if not missing_ids:
            return []
        with PostDb() as post_db:
            missing_posts = [post_db.posts.get(id=id) for id in missing_ids]
        if not missing_posts:
            e_binder.event_generate(BINDING.ON_LOAD_RIGHT_SET, len(missing_posts), "")
            return

        logger.info("Downloading %d missing posts for %s", len(missing_posts), artist)
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
            e_binder.event_generate(
                BINDING.ON_LOAD_RIGHT_SET, len(missing_posts), "Downloading: "
            )
            for future in concurrent.futures.as_completed(future_to_pid.keys()):
                try:
                    result = future.result()
                    e_binder.event_generate(BINDING.ON_LOAD_RIGHT_INCR)
                    if self.stop_event and self.stop_event.is_set():
                        logger.warning("Stop Event Recieved.")
                        executor.shutdown(wait=True, cancel_futures=True)
                        return
                    if isinstance(result, PostFile):
                        success_list.append(result)
                except Exception as e:
                    logger.error(e)

                    failure_list.append(future_to_pid[future])
            if failure_list:
                logger.error("The following IDs failed to load. %s", failure_list)

        logger.info("Adding Entries to PostFile Table.")
        with PostDb() as post_db:
            for post_file in success_list:
                if not self.update_post_file(post_db, post_file):
                    logger.debug("Did not update Postfile with id %s", post_file.id)
        return success_list

    def update_post_file(self, post_db: PostDb, store_post: PostFile):
        pid = store_post.id
        post = post_db.posts.get(id=pid)
        if not post:
            logger.warning("No post for id %s", pid)

            return False
        post_file = PostFile(
            id=post.id,
            ext_id=post.ext_id,
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
        return post_db.files.insert(post_file)

    def update_post_file_table(self, artist, repair=False):
        logger.info(
            "Updating PostFile Table for %s, %s, %s", self.store, self.board, artist
        )
        e_binder.event_generate(BINDING.ON_LOAD_MID_SET, "Updating PostFile table")
        store_posts: dict[str, PostFile] = self.store_handler.get_posts(
            str(self.board), artist
        )
        logger.info("store_posts recieved with %s records.", len(store_posts))
        inserted_list = []

        with PostDb() as post_db:
            for pid, store_post in store_posts.items():
                if store_post:
                    inserted = self.update_post_file(post_db, store_post)
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

    def update_board_artist_tag_counts(self, board, artist_list):
        board_map = defaultdict(int)
        with PostDb() as post_db:
            for artist in artist_list:
                artist_map = defaultdict(int)
                posts: list[Post] = post_db.posts.get_all(
                    artist_name=artist, board=board
                )
                for post in posts:
                    for tag in post.tags:
                        artist_map[tag] += 1
                        board_map[tag] += 1

                artist_tag_count_list = [
                    ArtistTagCount(artist, tag, count)
                    for tag, count in artist_map.items()
                ]
                post_db.artist_tag_counts.insert_many(artist_tag_count_list)

            board_tag_count_list = [
                ArtistTagCount(board, tag, count) for tag, count in board_map.items()
            ]
            post_db.artist_tag_counts.insert_many(board_tag_count_list)

    def update_tag_types(self):
        type_tags = self.board_handler.get_type_tags()
        with PostDb() as post_db:
            for type_, tags in type_tags.items():
                post_db.update_tag_types(tags, type_)

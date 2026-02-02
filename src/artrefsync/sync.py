from asyncio import Event
from concurrent.futures import ThreadPoolExecutor
import os
import time
import sqlite3
import threading
from collections import defaultdict

import concurrent
from artrefsync.boards.danbooru_handler import danbooru_handler
from artrefsync.boards.board_handler import ImageBoardHandler, Post, PostFile
from artrefsync.boards.rule34_handler import r34_handler
from artrefsync.boards.e621_handler import e621_handler
from artrefsync.stats import stats
from artrefsync.utils.EventManager import ebinder

from artrefsync.db.db_utils import BlobDb
from artrefsync.db.post_db import PostDb

# from artrefsync.db.dataclass_db import Dataclass_DB
from artrefsync.snail import Snail
from artrefsync.stores.storage import ImageStorage
from artrefsync.stores.plain_file_storage import PlainLocalStorage
from artrefsync.stores.eagle_storage import EagleHandler
from artrefsync.config import config
from artrefsync.constants import (
    BINDING,
    DANBOORU,
    LOCAL,
    R34,
    E621,
    TABLE,
    STORE,
    EAGLE,
    BOARD,
    APP,
)
from artrefsync.stores.link_cache import Link_Cache


import logging

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


def sync_config(event: Event = Event()):
    limit = config[TABLE.APP][APP.LIMIT]

    # Change scope to only allow one store
    store = None
    if config[TABLE.LOCAL][LOCAL.ENABLED]:
        store = PlainLocalStorage()
        # stores.append(store)

    # EAGLE Overrides the normal FS storage.
    if config[TABLE.EAGLE][EAGLE.ENABLED]:
        store = EagleHandler()
        # store.append(store)

    if store == None:
        logger.warning("NO STORE ENABLED. ENDING SYNC")
        return
        
    if config[TABLE.E621][E621.ENABLED]:
        logger.info("Syncing %s with store: %s", TABLE.E621, store.get_store())
        board = e621_handler
        sync(board, store, limit, event)

    if config[TABLE.R34][R34.ENABLED]:
        logger.info("Syncing %s with store: %s", TABLE.R34, store.get_store())
        board = r34_handler
        sync(board, store, limit, event)

    if config[TABLE.DANBOORU][DANBOORU.ENABLED]:
        logger.info("Syncing %s with store: %s", TABLE.DANBOORU, store.get_store())
        board = danbooru_handler
        sync(board, store, limit, event)

    ebinder.event_generate(BINDING.ON_LOADING_DONE)

def sync(
    board: ImageBoardHandler,
    store: ImageStorage,
    max_per_artist=10000,
    event: Event = Event(),
):
    logger.info(
        "Syncing %s to %s", board.get_board(), ", ".join(board.get_artist_list())
    )
    tag_post_dict = defaultdict(set)
    board_tag_count = defaultdict(int)
    inserted_success = 0
    inserted_fail = 0
    updated_posts = []
    artist_list = board.get_artist_list()
    store.create_board_and_artist_folders(board.get_board(), artist_list)
    cache = Link_Cache()

    loading_text = f"{board.get_board()} to {store.get_store()}"
    ebinder.event_generate(BINDING.ON_LOAD_LEFT_SET, len(artist_list))
    for i, artist in enumerate(artist_list):
        ebinder.event_generate(BINDING.ON_LOAD_LEFT_INCR, f"{board.get_board()}: {artist}")
        artist_tag_count = defaultdict(int)
        missing_file_posts = []
        store_posts: dict[str, Post] = store.get_posts(str(board.get_board()), artist)
        logger.info("Getting for %s", artist)
        board_posts = board.get_posts(artist, stop_event= event)
        if event and event.is_set():
            logger.info("STOP event received. Canceling tasks")
            return None
            
        logger.info("Inserting for %s", artist)

        with PostDb() as post_db:
            for pid, post in board_posts.items():
                # TODO fix this.
                # Check if records need to be updated.
                updated_or_new = True
                tag_post_dict[str(board.get_board())].add(pid)
                tag_post_dict[artist].add(pid)
                tag_post_dict[post.ext].add(pid)
                board_tag_count[post.ext] += 1
                artist_tag_count[post.ext] += 1

                if pid in store_posts:
                    store_post = store_posts[pid]
                    tag_dif = set(post.tags).difference(store_post.tags)
                    if len(tag_dif) > 0:
                        logger.info("Updating store post: %s with %d new tags: %s", pid, len(tag_dif), tag_dif)
                        store_post.tags = list(set(post.tags).union(store_posts[pid].tags))
                        store.update_post(store_post)
                        updated_posts.append(pid)

                if updated_or_new:
                    inserted_success += 1
                    post_db.posts.insert(post)
                for tag in post.tags:
                    board_tag_count[tag] += 1
                    artist_tag_count[tag] += 1
                    tag_post_dict[tag].add(pid)

                if pid not in post_db.files or not os.path.isfile(post_db.files[pid].file):
                    if pid in store_posts:
                        store_p = store_posts[pid]
                        thumbnail = store.get_thumbnail(store_p)
                        post_db.files.insert(
                            PostFile(
                                id=store_p.id,
                                ext_id=store_p.ext_id,
                                artist_name=store_p.artist_name,
                                store=store.get_store(),
                                board=board.get_board(),
                                height=store_p.height,
                                width=store_p.width,
                                ratio=store_p.ratio,
                                ext=store_p.ext,
                                thumbnail=thumbnail,
                                file=store_p.file,
                            )
                        )
                    else:
                        missing_file_posts.append(pid)
            post_db.artist_tags.dumps_blob(artist, artist_tag_count)
            

        
        missing_count = len(missing_file_posts)
        if missing_count > 0:
            ebinder.event_generate(BINDING.ON_LOAD_RIGHT_SET, missing_count, "Downloading: ")
            with (
                ThreadPoolExecutor() as executor,
            ):
                future_to_pid = {
                    executor.submit(
                        store.save_post, board_posts[pid], cache, event
                    ): pid
                    for pid in missing_file_posts
                    if pid in board_posts
                }
                count = 0
                for future in concurrent.futures.as_completed(future_to_pid.keys()):
                    try:
                        future.result()
                        ebinder.event_generate(BINDING.ON_LOAD_RIGHT_INCR)
                        # print(future)
                        count += 1
                        if event and event.is_set():
                            logger.warning("Stop Event Recieved.")
                            executor.shutdown(wait=True, cancel_futures=True)
                            return
                    except Exception as e:
                        logger.error(e)
                        event.set()
                        executor.shutdown(wait=True, cancel_futures=True)

            time.sleep(0.1)
            found_posts = set()
            for retry in range(5):
                curr_store_posts = store.get_posts(board.get_board(), artist)
                with PostDb() as post_db:
                    for missing_pid in missing_file_posts:
                        if (
                            missing_pid not in found_posts
                            and missing_pid in curr_store_posts
                        ):
                            # store.get

                            store_p = curr_store_posts[missing_pid]

                            thumbnail = None
                            retries = 3
                            for retry in range(1, 1 + retries):
                                try:
                                    thumbnail = store.get_thumbnail(store_p)
                                except:
                                    logger.error(
                                        "Getting thumbnail for %s failed (attempt %i/%i).",
                                        missing_pid,
                                        retry,
                                        retries,
                                    )
                                    pass

                            post_db.files.insert(
                                PostFile(
                                    id=store_p.id,
                                    ext_id=store_p.ext_id,
                                    store=store.get_store(),
                                    board=board.get_board(),
                                    artist_name=store_p.artist_name,
                                    height=store_p.height,
                                    width=store_p.width,
                                    ratio=store_p.ratio,
                                    ext=store_p.ext,
                                    thumbnail=thumbnail,
                                    file=store_p.file,
                                )
                            )
                            found_posts.add(missing_pid)
                missing_file_posts = [
                    x for x in missing_file_posts if x not in found_posts
                ]
                if len(missing_file_posts) == 0:
                    break
                logger.info(
                    f"Waiting for {len(missing_file_posts)} files to be downloaded...."
                )
                logger.info(
                    "Waiting on %i files. Pausing for %.2f seconds. Remaining posts: %i.",
                    len(missing_file_posts),
                    retry + 1,
                    missing_count - (len(curr_store_posts) - len(store_posts)),
                )
                time.sleep(retry + 1)
    with PostDb() as post_db:
        logger.info(
            "Inserting for %s, Updates %s, No Change: %s",
            artist,
            inserted_success,
            inserted_fail,
        )
        post_db.artist_tags.dumps_blob(str(board.get_board), board_tag_count)
        for tag, posts in tag_post_dict.items():
            post_db.tag_posts.union_update(tag, posts)
        logger.info("Updating %s tags", len(tag_post_dict))
    
    cache.close()

if __name__ == "__main__":
    event = Event()
    thread = threading.Thread(target=sync_config)
    thread.start()
    thread.join()

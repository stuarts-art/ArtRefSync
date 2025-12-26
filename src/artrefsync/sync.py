from asyncio import Event
from concurrent.futures import ThreadPoolExecutor
import time

import concurrent
from artrefsync.boards.board_handler import ImageBoardHandler
from artrefsync.boards.rule34_handler import r34_handler
from artrefsync.boards.e621_handler import e621_handler

from artrefsync.snail import Snail
from artrefsync.stores.storage import ImageStorage
from artrefsync.stores.plain_file_storage import PlainLocalStorage
from artrefsync.stores.eagle_storage import eagle_handler
from artrefsync.config import config
from artrefsync.constants import LOCAL, R34, E621, TABLE, STORE, EAGLE, BOARD, APP
from artrefsync.stores.link_cache import Link_Cache

import logging

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


def sync_config(event: Event = None):
    limit = config[TABLE.APP][APP.LIMIT]

    stores = []
    if config[TABLE.LOCAL][LOCAL.ENABLED]:
        store = PlainLocalStorage()
        stores.append(store)

    if config[TABLE.EAGLE][EAGLE.ENABLED]:
        store = eagle_handler
        stores.append(store)

    if config[TABLE.E621][E621.ENABLED]:
        logger.info("Syncing %s with stores: %s", TABLE.E621, list(s.get_store() for s in stores))
        board = e621_handler
        sync(board, stores, limit, event)

    if config[TABLE.R34][R34.ENABLED]:
        logger.info("Syncing %s with stores: %s", TABLE.R34, list(s.get_store() for s in stores))
        board = r34_handler
        sync(board, stores, limit, event)


def sync(
    board: ImageBoardHandler,
    stores: list[ImageStorage],
    max_per_artist=10000,
    event: Event = None
):
    logger.info("Syncing %s to %s", board.get_board(), ', '.join(board.get_artist_list()))
    # First, get posts from board
    for artist in board.get_artist_list():
        if event and event.is_set():
            logger.warning("Stop Event Recieved.")
            return

        logger.info("%s - getting external post metadata for %s", board.get_board(), artist)
        posts = board.get_posts(artist)
        logger.info("%s with %s from board.", artist, len(posts))


        with Link_Cache() as cache:
            for store in stores:
                if event and event.is_set():
                    logger.warning("Stop Event Recieved.")
                    return
                logger.info("%s - Getting internal posts meta data for %s", store.get_store(), artist)
                store_posts = store.get_posts(board.get_board(), artist)
                missing_posts = set(posts.keys()).difference(set(store_posts.keys()))

                logger.info("Missing post count: %s", len(missing_posts))
                if len(missing_posts) == 0:
                    continue

                count = 0

                start_time = time.time()

                with ThreadPoolExecutor() as executor, Snail(len(missing_posts), f"{artist} - {len(missing_posts)}") as snail:
                    if event and event.is_set():
                        logger.warning("Stop Event Recieved.")
                        executor.shutdown(wait=True, cancel_futures=True)
                        return
                    futures = [executor.submit(store.save_post, posts[pid], cache, event) for pid in missing_posts]
                    for future in concurrent.futures.as_completed(futures):
                        count += 1
                        # logger.info(future)
                        snail.load(count)
                        if event and event.is_set():
                            logger.warning("Stop Event Recieved.")
                            executor.shutdown(wait=True, cancel_futures=True)
                            return
                    
                execution_time = time.time() - start_time
                logger.info("Finished in %.2f seconds", execution_time)

                for retry in range(3):
                    curr_store_posts = store.get_posts(board.get_board(), artist)
                    if len(curr_store_posts) - len(store_posts) < len(missing_posts):
                        logger.info("Pausing for %.2f seconds. Remaining posts: %i.", 
                                    retry+1, len(curr_store_posts) - len(store_posts))
                        time.sleep(retry + 1)
                    else:
                        break

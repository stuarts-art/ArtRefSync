import time
from artrefsync.boards.board_handler import ImageBoardHandler
from artrefsync.boards.rule34_handler import R34Handler
from artrefsync.boards.e621_handler import E621Handler

from artrefsync.stores.storage import ImageStorage
from artrefsync.stores.plain_file_storage import PlainLocalStorage
from artrefsync.stores.eagle_storage import EagleHandler
from artrefsync.config import Config
from artrefsync.constants import LOCAL, R34, E621, TABLE,STORE, EAGLE, BOARD


def sync_config(config: Config = Config()):
    limit = config[TABLE.APP]["limit"]

    stores = []
    if config[TABLE.LOCAL][LOCAL.ENABLED]:
        store = PlainLocalStorage(config)
        stores.append(store)

    if config[TABLE.EAGLE][EAGLE.ENABLED]:
        store = EagleHandler(config)
        stores.append(store)

    if config[TABLE.E621][E621.ENABLED]:
        print(f"Syncing {TABLE.E621} with stores: {list(s.get_store() for s in stores)}")
        artist_list = config[TABLE.E621][E621.ARTISTS]
        board = E621Handler(config)
        sync(board, stores, artist_list, limit)

    if config[TABLE.R34][R34.ENABLED]:
        print(f"Syncing {TABLE.R34} with stores: {list(s.get_store() for s in stores)}")
        artist_list = config[TABLE.R34][R34.ARTISTS]
        board = R34Handler(config)
        sync(board, stores, artist_list, limit)


def sync(
    board: ImageBoardHandler,
    stores: list[ImageStorage],
    artist_list: list[str],
    max_per_artist=10000,
):
    print(f"Syncing {board} to {', '.join(artist_list)}")

    # First, get posts from board
    for artist in artist_list:
        print(f"{board.get_board()} - Getting external posts meta data for {artist}.")
        posts = board.get_posts(artist)

        for store in stores:
            post_count = 0
            print(f"{store.get_store()} - Getting internal posts meta data for {artist}.")
            store_posts = store.get_posts(board.get_board(), artist)
            # print(store_posts)


            last_ran = time.time()
            min_time = .1
            for pid, post in posts.items():
                if pid not in store_posts:
                    if post_count % 10 == 0:
                        print(post)
                    store.save_post(post)
                    curr_time = time.time()
                    if curr_time - last_ran < min_time:
                        time.sleep(min_time - (curr_time - last_ran))
                    last_ran = curr_time

                    post_count += 1
                    if post_count > max_per_artist:
                        break

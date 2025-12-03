from artrefsync.boards.board_handler import ImageBoardHandler
from artrefsync.boards.rule34_handler import R34Handler
from artrefsync.boards.e621_handler import E621Handler

from artrefsync.stores.storage import ImageStorage
from artrefsync.stores.plain_file_storage import PlainLocalStorage
from artrefsync.config import Config
from artrefsync.constants import LOCAL, R34, E621, TABLE


def sync_config(config: Config = Config()):
    limit = config[TABLE.APP]["limit"]

    stores = []
    if config.getLOCAL(LOCAL.ENABLED):
        store = PlainLocalStorage(config)
        stores.append(store)

    if config.getE621(E621.ENABLED):
        artist_list = config.getE621(E621.ARTISTS)
        board = E621Handler(config)
        sync(board, stores, artist_list, limit)

    if config.getR34(R34.ENABLED):
        artist_list = config.getR34(R34.ARTISTS)
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
        print(f"{board.get_board()} - Getting posts meta data for {artist}.")
        posts = board.get_posts(artist)

        for store in stores:
            post_count = 0
            print(f"{board.get_board()} - Getting posts meta data for {artist}.")
            store_posts = store.get_posts(board.get_board, artist)

            for pid, post in posts.items():
                if pid not in store_posts:
                    store.save_post(post)
                    post_count += 1
                    if post_count > max_per_artist:
                        break

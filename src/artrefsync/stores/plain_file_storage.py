import json
from pathlib import Path
import requests
import artrefsync.stats as stats
from artrefsync.stores.storage import ImageStorage
from artrefsync.constants import BOARD, LOCAL, STATS, STORE, TABLE
from artrefsync.boards.board_handler import Post
from artrefsync.config import Config


def main():
    config = {TABLE.LOCAL: {LOCAL.ARTIST_FOLDER: "artists"}}
    plain_storage = PlainLocalStorage(config)


class PlainLocalStorage(ImageStorage):
    def __init__(self, config: Config):
        self.artist_folder = Path(config[TABLE.LOCAL][LOCAL.ARTIST_FOLDER])
        self.board_artist_posts = {}
        self.board_artist_paths = {}
        self.board_paths = {}

        if not Path.exists(self.artist_folder):
            Path.mkdir(self.artist_folder)
        for board in BOARD:
            self.board_artist_posts[board] = {}
            self.board_artist_paths[board] = {}
            board_path = Path.joinpath(self.artist_folder, board)
            self.board_paths[board] = board_path
            if not Path.exists(board_path):
                Path.mkdir(board_path)
            # get artists from board_path
            for artist_path in Path.iterdir(board_path):
                artist_name = artist_path.name
                self.board_artist_posts[board][artist_name] = {}
                self.board_artist_paths[board][artist_name] = artist_path

                for post in Path.iterdir(board_path):
                    if post.suffix == ".json":
                        pid = post.name.split("-", maxsplit=1)[0]
                        self.board_artist_posts[board][artist_name][pid] = post

    def get_store(self):
        return STORE.LOCAL

    def get_posts(self, board: BOARD, artist: str):
        if board in self.board_artist_posts:
            if artist in self.board_artist_posts[board]:
                return self.board_artist_posts[board][artist]
        return {}

    def save_post(self, post: Post):
        board = post.board
        artist = post.artist_name
        # create artist folder if it does not exist.
        board_path = self.board_paths[board]
        artist_path = Path.joinpath(board_path, artist)
        if not Path.exists(artist_path):
            Path.mkdir(artist_path)
            self.board_artist_paths[artist] = artist_path

        try:
            img_data = requests.get(post.url, timeout=10.0).content
            file_name = artist_path.joinpath(post.name + Path(post.url).suffix)
            with open(file_name, "wb") as f:
                f.write(img_data)
            post.file = file_name
            file_metadata_name = artist_path.joinpath(post.name + ".json")
            with open(file_metadata_name, "w") as f:
                json.dump(post.__dict__, f, indent=4)

        except Exception:
            stats.add(STATS.FAILED_COUNT, 1)

    def update_post(self, board: BOARD, post: Post):
        # No Metadata is saved...right?
        pass


if __name__ == "__main__":
    main()

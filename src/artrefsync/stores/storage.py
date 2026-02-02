from abc import ABC, abstractmethod
from asyncio import Event
from artrefsync.boards.board_handler import Post
from artrefsync.stores.link_cache import Link_Cache
from artrefsync.constants import BOARD, STORE


class ImageStorage(ABC):
    @abstractmethod
    def get_store(self) -> STORE:
        pass

    @abstractmethod
    def get_posts(self, board: BOARD, artist: str) -> dict[str, Post]:
        pass

    @abstractmethod
    def create_board_and_artist_folders(self, board: BOARD, artists: list[str]):
        pass

    @abstractmethod
    def save_post(self, post: Post, link_cache: Link_Cache = None, event: Event = None):
        pass

    @abstractmethod
    def update_post(self, post: Post):
        pass

    @abstractmethod
    def get_thumbnail(self, post: Post):
        pass

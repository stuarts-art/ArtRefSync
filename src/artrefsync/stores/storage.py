from abc import ABC, abstractmethod
from artrefsync.boards.board_handler import Post
from artrefsync.constants import BOARD, STORE


class ImageStorage(ABC):
    @abstractmethod
    def get_store(self) -> STORE:
        pass

    @abstractmethod
    def get_posts(self, board: BOARD, artist:str) -> dict[str, Post]:
        pass

    @abstractmethod
    def save_post(self, post: Post):
        pass

    @abstractmethod
    def update_post(self, post: Post):
        pass
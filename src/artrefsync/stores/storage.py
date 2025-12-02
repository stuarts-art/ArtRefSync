from abc import ABC, abstractmethod
from artrefsync.boards.board_handler import Post
from artrefsync.constants import BOARD


class ImageStorage(ABC):

    @abstractmethod
    def get_posts(self, board: BOARD, artist:str):
        pass

    @abstractmethod
    def save_post(self, post: Post):
        pass

    @abstractmethod
    def update_post(self, post: Post):
        pass
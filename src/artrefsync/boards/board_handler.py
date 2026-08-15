from abc import ABC, abstractmethod

from artrefsync.boards.board_models import Post
from artrefsync.constants import BOARD


class ImageBoardHandler(ABC):
    @abstractmethod
    def get_posts(self, tag, post_limit=None) -> dict[str, Post]:
        pass

    @abstractmethod
    def get_board(self) -> BOARD:
        pass

    @abstractmethod
    def get_artist_list(self) -> list[str]:
        pass

    @abstractmethod
    def get_type_tags(self) -> dict[str, str]:
        pass

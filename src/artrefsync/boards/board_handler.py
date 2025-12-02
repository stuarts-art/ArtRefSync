from abc import ABC, abstractmethod
from dataclasses import dataclass
from artrefsync.constants import BOARD

@dataclass
class Post():
    id: str
    artist_name: str
    name: str
    url: str
    tags: list[str]
    website:str
    board: BOARD

    def __str__(self):
        return f"{self.name} - {self.url}"
        

class ImageBoardHandler(ABC):
    @abstractmethod
    def get_posts(self, tag, post_limit=None) -> dict[str, Post]:
        pass

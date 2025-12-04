from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
from artrefsync.constants import BOARD

@dataclass_json
@dataclass
class Post():
    id: str
    artist_name: str
    name: str
    url: str
    tags: list[str]
    website:str
    board: BOARD
    file: str = field(default="")

    def __str__(self):
        return f"{self.name} - {self.url}"
        

class ImageBoardHandler(ABC):
    @abstractmethod
    def get_posts(self, tag, post_limit=None) -> dict[str, Post]:
        pass

    @abstractmethod 
    def get_board(self) -> BOARD:
        pass


if __name__ == "__main__":
    import json
    p = Post("a", "Artist name", "name", "url str", ["tag1", "tag2"], "website", str(BOARD.E621))
    with open("test.json", "w") as f:
        json.dump(p.__dict__, f)
    print (p.__dict__)
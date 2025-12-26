from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
from artrefsync.constants import BOARD, TABLE, APP
from artrefsync.config import config

@dataclass_json
@dataclass
class Post():
    id: str             # Centralized App ID
    ext_id: str         # external id (When from Board->BoardID, Store -> StoreID)
    name: str           # Name of file/post
    artist_name: str
    tags: list[str]
    board: BOARD | None
    score: str | None
    url: str | None
    website:str | None
    file: str = field(default="")

    def __post_init__(self):
        self.storage_id = self.name[:self.name.find('-')]

    def __str__(self):
        return f"{self.name} - {self.url}"
        
    @staticmethod
    def make_storage_id(raw_id, board: BOARD) -> str:
        return f"{str(raw_id).zfill(int(config[TABLE.APP][APP.ID_LENGTH]))}.{board}"
        
    
    @staticmethod
    def check_id(id_str:str) -> bool:
        id_split = id_str.split('.', maxsplit=1)
        if (
            len(id_split) != 2 or
            not id_split[0].isdigit() or
            id_split[1] not in BOARD
            ):
            return False
        return True

    @staticmethod
    def parse_id(id_str:str) -> bool:
        id_split = id_str.split('-', maxsplit=1)
        if len(id_split) == 1 or id_split[0] == "":
            return id_str
        return id_split[0]


class ImageBoardHandler(ABC):
    @abstractmethod
    def get_posts(self, tag) -> dict[str, Post]:
        pass

    @abstractmethod 
    def get_board(self) -> BOARD:
        pass

    def get_artist_list(self) -> BOARD:
        pass

if __name__ == "__main__":

    print("")
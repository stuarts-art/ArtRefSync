from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from threading import Event
from dataclasses_json import dataclass_json
from artrefsync.constants import BOARD, TABLE, APP, STORE
from artrefsync.config import config


# @dataclass_json
@dataclass
class Post:
    id: str  # Centralized App ID
    ext_id: str  # external id (When from Board->BoardID, Store -> StoreID)
    name: str  # Name of file/post
    artist_name: str
    tags: list[str]
    board: BOARD | None
    score: int | None
    url: str | None
    website: str | None
    board_update_str: str | None = field(default=None)
    height: int | None = field(default=0)
    width: int | None = field(default=0)
    ratio: float | None = field(default=None)
    file: str | None = field(default="")
    ext: str = field(default="")
    thumbnail: str | None = field(default="")

    def __post_init__(self):
        self.storage_id = self.name[: self.name.find("-")]

    def __str__(self):
        return f"{self.name} - {self.url}"

    @staticmethod
    def make_storage_id(raw_id, board: BOARD) -> str:
        return f"{str(raw_id).zfill(int(config[TABLE.APP][APP.ID_LENGTH]))}.{board}"

    @staticmethod
    def check_id(id_str: str) -> bool:
        id_split = id_str.split(".", maxsplit=1)
        if len(id_split) != 2 or not id_split[0].isdigit() or id_split[1] not in BOARD:
            return False
        return True

    @staticmethod
    def parse_id(id_str: str) -> bool:
        id_split = id_str.split("-", maxsplit=1)
        if len(id_split) == 1 or id_split[0] == "":
            return id_str
        return id_split[0]


@dataclass
class PostFile:
    id: str  # Centralized App ID
    ext_id: str  # external id (When from Board->BoardID, Store -> StoreID)
    store: STORE | None
    board: BOARD | None
    artist_name: str | None = field(default="")
    height: int | None = field(default=0)
    width: int | None = field(default=0)
    ratio: float | None = field(default=None)
    ext: str = field(default="")
    thumbnail: str | None = field(default="")
    file: str | None = field(default="")


class ImageBoardHandler(ABC):
    @abstractmethod
    def get_posts(self, tag, post_limit=None, stop_event: Event=None) -> dict[str, Post]:
        pass

    @abstractmethod
    def get_board(self) -> BOARD:
        pass

    def get_artist_list(self) -> list[str]:
        pass


if __name__ == "__main__":
    print("")

    types_list = Post.__doc__[5:-1].split(", ")
    types_dict = {}
    for f in types_list:
        f_split = f.split(":")
        # print(f_split)
        types_dict[f_split[0]] = f_split[1].strip().split(" = ")[0].split(" | ")

    # print(types_list)
    print(types_dict)

    p = Post

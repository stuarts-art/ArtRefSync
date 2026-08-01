from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Annotated

from artrefsync.config import get_config
config = get_config()
from artrefsync.constants import APP, BOARD, STORE, TABLE


# @dataclass_json
@dataclass
class Post:
    id: str
    ext_id: Annotated[str, "UNIQUE"]  # external id (When from Board->BoardID, Store -> StoreID)
    name: str = ""
    artist_name: str = ""
    tags: list[str] | None = None
    board: Annotated[BOARD | None, "UNIQUE"] = None
    score: int | None = 0
    url: str | None = ""
    website: str = ""
    md5:str = ""   
    update_timestamp: int | None = 0
    create_timestamp: int | None = 0
    height: int | None = 0
    width: int | None = 0
    ratio: float | None = 0.0
    ext: str = ""
    file_link: str | None = ""
    sample_link: str | None = ""
    preview_link: str | None = ""
    sql_id: Annotated[int | None, "PRIMARY KEY"] = None

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
    id: Annotated[str, "PRIMARY KEY"]  # Centralized App ID
    ext_id: str  # external id (When from Board->BoardID, Store -> StoreID)
    store: STORE | None
    board: BOARD | None
    artist_name: str | None = field(default="")
    height: int | None = field(default=0)
    width: int | None = field(default=0)
    ratio: float | None = field(default=None)
    ext: str = field(default="")
    preview: str | None = field(default="")
    sample: str | None = field(default="")
    thumbnail: str | None = field(default="")
    file: str | None = field(default="")


class ImageBoardHandler(ABC):
    @abstractmethod
    def get_posts(
        self, tag, post_limit=None
    ) -> dict[str, Post]:
        pass

    @abstractmethod
    def get_board(self) -> BOARD:
        pass

    @abstractmethod
    def get_artist_list(self) -> list[str]:
        pass

    @abstractmethod
    def get_type_tags(self) -> dict[str,str]:
        pass
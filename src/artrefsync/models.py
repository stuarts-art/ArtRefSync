from dataclasses import dataclass
import json
from typing import Optional


@dataclass
class EagleItem:
    id: str
    name: str
    size: int
    ext: str
    tags: list[str]
    folders: list[str]
    isDeleted: bool
    url: str


@dataclass
class EagleMetaData:
    id: str
    name: str
    size: int
    btime: int
    mtime: int
    ext: str
    tags: list[str]
    folders: list[str]
    isDeleted: bool
    url: str
    annotation: str
    modificationTime: int
    height: Optional[int]
    width: Optional[int]
    palettes: Optional[list]
    lastModified: Optional[int]

    def to_file_str(self):
        return json.dumps(self.__dict__, separators=(",", ":"))

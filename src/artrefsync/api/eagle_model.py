from dataclasses import dataclass
import json
from typing import List, Optional
from dacite import from_dict


# API found: https://api.eagle.cool/
class EagleFolder:
    @dataclass
    class UpdatedFolder:
        id: str
        name: str
        description: str | None
        modificationTime: int
        children: List["EagleFolder.UpdatedFolder"]
        size: int
        descendantImageCount: int

    @dataclass
    class CreatedFolder:
        id: str
        name: str
        images: list[str]
        folders: list[str]
        modificationTime: int
        imagesMappings: dict | None
        tags: list[str]
        children: list["EagleFolder.CreatedFolder"]
        isExpand: bool | None

    @dataclass
    class ListFolder:
        id: str
        name: str
        description: str | None
        children: List["EagleFolder.ListFolder"]
        modificationTime: int
        tags: List[str]
        imageCount: int | None
        descendantImageCount: int | None
        pinyin: str | None
        extendTags: List[str] | None
        orderBy: str | None
        sortIncrease: bool | None


class EagleItem:

    @dataclass
    class Pallete:
        color: list[int]
        ratio: float

    @dataclass
    class UpdatedItem:
        id: str
        name: str
        size: int
        ext: str
        tags: list[str] | None
        folders: list[str] | None
        isDeleted: bool
        url: str | None
        annotation: str | None
        modificationTime: int | None
        height: int | None
        width: int | None
        noThumbnail: bool | None
        lastModified: int | None
        palettes: list["EagleItem.Pallete"] | None
        star: int | None

    @dataclass
    class Item:
        id: str
        name: str
        size: int
        ext: str
        tags: list[str]
        folders: list[str] | None
        # isDeleted: bool | None
        url: str | None
        annotation: str | None
        modificationTime: int | None
        height: int | None
        width: int | None
        # lastModified: int | None


    @dataclass
    class Metadata:
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


class EagleLibrary:
    @dataclass
    class Info:
        folders: List["EagleLibrary.Info.EagleFolder"] | None
        smartFolders: List["EagleLibrary.Info.SmartFolder"] | None
        quickAccess: List[dict] | None
        tagsGroups: List["EagleLibrary.Info.TagGroups"] | None
        modificationTime: int
        applicationVersion: str

        @dataclass
        class EagleFolder:
            id: str
            name: str
            description: str
            children: List["EagleLibrary.Info.EagleFolder"]
            modificationTime: int
            tags: List[str]
            iconColor: str | None
            password: str | None
            passwordTips: str | None
            coverId: str | None
            orderBy: str | None
            sortIncrease: bool | None

        @dataclass
        class Rule:
            hashkey: str | None
            method: str
            property: str
            value: list | str | int

        @dataclass
        class Condition:
            hashKey: str | None
            match: str
            rules: list["EagleLibrary.Info.Rule"]

        @dataclass
        class SmartFolder:
            id: str
            icon: str | None
            name: str
            description: str
            modificationTime: int
            conditions: list["EagleLibrary.Info.Condition"]
            orderBy: str | None
            sortIncrease: bool | None

        @dataclass
        class TagGroups:
            id: str
            name: str
            tags: List[str]
            color: str | None

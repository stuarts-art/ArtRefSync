from __future__ import annotations

import json
from dataclasses import dataclass


# API found: https://api.eagle.cool/
class EagleFolder:
    @dataclass
    class UpdatedFolder:
        id: str
        name: str
        description: str | None
        modificationTime: int
        children: list[EagleFolder.UpdatedFolder]
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
        children: list[EagleFolder.CreatedFolder]
        isExpand: bool | None

    @dataclass
    class ListFolder:
        id: str
        name: str
        description: str | None
        children: list[EagleFolder.ListFolder]
        modificationTime: int
        tags: list[str]
        imageCount: int | None
        descendantImageCount: int | None
        pinyin: str | None
        extendTags: list[str] | None
        orderBy: str | None
        sortIncrease: bool | None


class EagleItem:

    @dataclass
    class Palette:
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
        palettes: list[EagleItem.Palette] | None
        star: int | None

    @dataclass
    class Item:
        id: str
        name: str
        size: int
        ext: str
        tags: list[str]
        folders: list[str] | None
        url: str | None
        annotation: str | None
        modificationTime: int | None
        height: int | None
        width: int | None

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
        height: int | None
        width: int | None
        palettes: list | None
        lastModified: int | None

        def to_file_str(self):
            return json.dumps(self.__dict__, separators=(",", ":"))


class EagleLibrary:
    @dataclass
    class Info:
        folders: list[EagleLibrary.Info.EagleFolder] | None
        smartFolders: list[EagleLibrary.Info.SmartFolder] | None
        quickAccess: list[dict] | None
        tagsGroups: list[EagleLibrary.Info.TagGroups] | None
        modificationTime: int
        applicationVersion: str

        @dataclass
        class EagleFolder:
            id: str
            name: str
            description: str
            children: list[EagleLibrary.Info.EagleFolder]
            modificationTime: int
            tags: list[str]
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
            rules: list[EagleLibrary.Info.Rule]

        @dataclass
        class SmartFolder:
            id: str
            icon: str | None
            name: str
            description: str
            modificationTime: int
            conditions: list[EagleLibrary.Info.Condition]
            orderBy: str | None
            sortIncrease: bool | None

        @dataclass
        class TagGroups:
            id: str
            name: str
            tags: list[str]
            color: str | None

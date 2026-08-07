from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, StrEnum

import dacite

config = dacite.Config(cast=[int, str], type_hooks={datetime: datetime.fromisoformat})


@dataclass
class E621_Post:
    id: int | str
    created_at: datetime
    updated_at: datetime
    file: File
    preview: Preview
    sample: Sample
    score: Score
    tags: Tags
    locked_tags: list[str]
    change_seq: float
    flags: Flags
    rating: Ratings
    fav_count: int
    sources: list[str]
    pools: list[int]
    relationships: Relationships
    approver_id: int | str | None
    uploader_id: int | str | None
    description: str | None
    comment_count: int | str | None
    is_favorited: bool
    has_notes: bool
    duration: float | None
    uploader_name: str

    @staticmethod
    def parse_e621_post(post_dict) -> E621_Post:
        return dacite.from_dict(E621_Post, post_dict, config=config)


class Ratings(StrEnum):
    s = "s"
    q = "q"
    e = "e"


@dataclass
class File:
    width: int | None
    height: int | None
    ext: str | None
    size: int | None
    md5: str | None
    url: str | None


@dataclass
class Preview:
    width: int | None
    height: int | None
    url: str | None


@dataclass
class Score:
    up: int
    down: int
    total: int


@dataclass
class Tags:
    general: list[str]
    artist: list[str]
    copyright: list[str]
    character: list[str]
    species: list[str]
    invalid: list[str]
    meta: list[str]
    lore: list[str]
    contributor: list[str]


@dataclass
class Flags:
    pending: bool
    flagged: bool
    note_locked: bool
    status_locked: bool
    rating_locked: bool
    deleted: bool


@dataclass
class Relationships:
    parent_id: int | str | None
    has_children: bool
    has_active_children: bool
    children: list[int]


class Type(Enum):
    flag = "flag"
    deletion = "deletion"


@dataclass
class PostSampleAlternate:
    fps: float
    codec: str
    size: int
    width: int
    height: int
    url: str


@dataclass
class Variants:
    webm: PostSampleAlternate | None = None
    mp4: PostSampleAlternate | None = None


@dataclass
class Samples:
    field_480p: PostSampleAlternate | None = None
    field_720p: PostSampleAlternate | None = None


@dataclass
class Alternates:
    has: bool | None = None
    original: PostSampleAlternate | None = None
    variants: Variants | None = None
    samples: Samples | None = None


@dataclass
class Sample:
    has: bool
    height: int
    width: int
    url: str | None
    alternates: Alternates

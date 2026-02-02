from dataclasses import dataclass
from typing import List

import dacite

config = dacite.Config(cast=[int], type_hooks={list[str]: (lambda x: x.split())})


@dataclass
class Danbooru_Post:
    id: int
    created_at: str
    uploader_id: int
    score: int
    source: str | None
    md5: str | None
    rating: str
    image_width: int
    image_height: int
    tag_string: list[str]
    fav_count: int
    file_ext: str
    tag_count_general: int | None
    tag_count_artist: int | None
    tag_count_character: int | None
    tag_count_copyright: int | None
    file_size: int
    up_score: int
    down_score: int
    is_pending: bool | None
    is_flagged: bool | None
    is_deleted: bool | None
    tag_count: int
    updated_at: str
    is_banned: bool | None
    tag_count_meta: int
    tag_string_general: list[str]
    tag_string_character: list[str]
    tag_string_copyright: list[str]
    tag_string_artist: list[str]
    tag_string_meta: list[str]
    file_url: str
    large_file_url: str
    preview_file_url: str


def parse_danbooru_post(post_dict) -> Danbooru_Post:
    post = dacite.from_dict(Danbooru_Post, post_dict, config=config)
    return post

from dataclasses import dataclass

import dacite

config = dacite.Config(cast=[int], type_hooks={list[str]: (lambda x: x.split())})

@dataclass
class TagInfo:
    count: int
    type: str
    tag: str

@dataclass
class R34_Post:
    height: int | None
    score: int | None
    file_url: str
    parent_id: str | int
    sample_url: str
    sample_width: int | None
    sample_height: int | None
    preview_url: str
    rating: str
    tags: list[str]
    id: int
    width: int | None
    change: int | None
    hash: str
    creator_id: int | None
    has_children: str | None
    status: str
    source: str
    has_notes: bool
    has_comments: str | None
    preview_width: int | None
    preview_height: int | None
    tag_info: list[TagInfo] | None


    @staticmethod
    def parse_r34_post(post_dict) -> R34_Post:
        post = dacite.from_dict(R34_Post, post_dict, config=config)
        return post

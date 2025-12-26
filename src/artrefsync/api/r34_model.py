
from dataclasses import dataclass
from typing import List

import dacite

config = dacite.Config(
    cast=[int],
    type_hooks={List[str]: (lambda x: x.split())}
)

@dataclass
class R34_Post():
    height: int | None
    score: int | None
    file_url: str
    parent_id: str
    sample_url: str
    sample_width: int | None
    sample_height: int | None
    preview_url: str
    rating: str
    tags: List[str]
    id: str
    width: int | None
    change: int | None
    md5: str
    creator_id: int | None
    has_children: str | None
    created_at: str
    status: str
    source: str
    has_notes: str
    has_comments: str
    preview_width: int | None
    preview_height: int | None   
    
def parse_r34_post(post_dict) -> R34_Post:
    post = dacite.from_dict(R34_Post, post_dict, config=config)
    return post
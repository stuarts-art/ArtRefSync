from dataclasses import dataclass


@dataclass
class Tag:
    tag: str

@dataclass
class TagType:
    tag: str
    type: str

@dataclass
class ArtistTagCount:
    artist: str
    tag: str
    count: int

@dataclass
class PostTagLink:
    pid: int # Post ID
    tid: int # Tag ID
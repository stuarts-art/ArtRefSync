from dataclasses import dataclass

@dataclass
class TagType:
    tag: str
    type: str

@dataclass
class ArtistTagCount:
    artist: str
    tag: str
    count: int
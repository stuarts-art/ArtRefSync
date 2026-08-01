from dataclasses import dataclass
from typing import Annotated


@dataclass
class Tag:
    tag: Annotated[str, "UNIQUE"] = ""
    sql_id: Annotated[int | None , "PRIMARY KEY"] = None

@dataclass
class TagType:
    tag_id: Annotated[str, "PRIMARY KEY", "REFERENCES Tag(sql_id)"] = ""
    type: Annotated[str, "PRIMARY KEY"] = ""

@dataclass
class ArtistTagCount:
    artist: Annotated[str, "PRIMARY KEY"]
    tag: Annotated[str, "PRIMARY KEY", "REFERENCES Tag(tag)"]
    count: int = 0

@dataclass
class PostTagLink:
    post_id: Annotated[int, "PRIMARY KEY", "REFERENCES Post(sql_id)"]
    tag_id: Annotated[int, "PRIMARY KEY", "REFERENCES Tag(sql_id)"]
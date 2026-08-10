from dataclasses import dataclass, field
from typing import Annotated

from artrefsync.constants import BOARD, STORE


@dataclass
class PostFile:
    id: Annotated[str, "PRIMARY KEY"]  # Centralized App ID
    ext_id: str  # external id (When from Board->BoardID, Store -> StoreID)
    store: STORE | None
    board: BOARD | None
    artist_name: str | None = field(default="")
    height: int | None = field(default=0)
    width: int | None = field(default=0)
    ratio: float | None = field(default=None)
    ext: str = field(default="")
    preview: str | None = field(default="")
    sample: str | None = field(default="")
    thumbnail: str | None = field(default="")
    file: str | None = field(default="")
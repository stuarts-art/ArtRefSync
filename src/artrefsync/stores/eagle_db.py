import json
import os
import sqlite3
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, ClassVar

from dataclassdb import DataclassDb, QueryBuilder

from artrefsync.api.eagle_client import EagleClient
from artrefsync.config import get_config
from artrefsync.constants import APP, EAGLE, TABLE

config = get_config()


def encode_dt_ms(dt: datetime) -> float:
    return dt.timestamp()


def decode_dt_ms(timestamp_ms: float) -> datetime:
    return datetime.fromtimestamp(timestamp_ms, UTC)


@dataclass
class Folder:
    id: Annotated[str, "PRIMARY KEY"]
    name: str
    modificationTime: Annotated[datetime, "REAL"]


@dataclass
class Children:
    parent_id: Annotated[str, "PRIMARY KEY", "REFERENCES Folder(id)"]
    child_id: Annotated[str, "PRIMARY KEY", "REFERENCES Folder(id)"]


class EagleDb:
    initialized = False
    metadata_file_map :ClassVar[dict[str, Path]]= {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.connection.commit()
        self.connection.close()

    def __contains__(self, name) -> bool:
        folder = self.folder.get(name=name)
        return folder is not None

    def __getitem__(self, key) -> Folder:
        return self.folder.get(name=key)

    def __init__(self, connection=None, client=None, refresh=True):
        self.library = config[TABLE.EAGLE][EAGLE.LIBRARY]
        self.artists_folder_name = config[TABLE.EAGLE][EAGLE.ARTIST_FOLDER]
        self.db_name = Path(config[TABLE.APP][APP.DB_DIR]) / "eagle.db"
        self.library_path_dict = {}
        self.client = client if client else EagleClient()
        self.connection = connection

        if not self.connection:
            db_dir = config[TABLE.APP][APP.DB_DIR]
            db_name = "eagle.db"
            if db_dir:
                db_file_name = config.resource_path(f"{db_dir}/{db_name}")
                os.makedirs(os.path.dirname(db_file_name), exist_ok=True)
            else:
                db_file_name = config.resource_path(db_name)
            self.connection = sqlite3.connect(db_file_name)
            self.connection_owner = True
        self.commit = self.connection.commit

        verify = not EagleDb.initialized
        self.folder: DataclassDb[Folder] = DataclassDb(
            Folder, self.connection, verify_table=verify
        )
        self.children: DataclassDb[Children] = DataclassDb(
            Children, self.connection, verify_table=verify
        )
        self.connection.commit()

        if verify or refresh:
            EagleDb.initialized = True
            self.folder.CREATE.INDEX.IF.NOT.EXISTS("folder_name_index").ON(Folder).par(
                "name"
            ).execute()

            if self.library not in EagleDb.metadata_file_map:
                EagleDb.metadata_file_map[self.library] = self.get_metadata_file()
            metadata_file = EagleDb.metadata_file_map[self.library]

            with open(metadata_file, "r") as file:
                parsed_metadata = json.load(file)

            folders_queue = deque()
            folders_queue.extend(parsed_metadata["folders"])
            artist_folder = None
            while len(folders_queue) > 0:
                folder = folders_queue.popleft()
                if folder["name"] == self.artists_folder_name:
                    artist_folder = folder
                else:
                    if "children" in folder:
                        folders_queue.extend(folder["children"])
            if artist_folder is None:
                return

            _, folders, relationships = self.parse_folder_dict(artist_folder, None)
            with DataclassDb(Folder, self.connection) as db:
                db.insert_many(folders)
            with DataclassDb(Children, self.connection) as db:
                db.insert_many(relationships)

    def get_sub_folders(self, folder_name) -> list[Folder]:
        parent = self.folder.get(name=folder_name)
        if not parent:
            return []

        qb = QueryBuilder()
        qb.SELECT("f.id", "f.name").from_(Folder, "f")
        qb.join(Children, "c", on="f.id = c.child_id")
        qb.WHERE("c.parent_id").eq("?")

        rows = self.folder.execute(parent.id, sql_str=str(qb))
        return {k: v for v, k in rows}

    def get_metadata_file(self) -> Path:
        history = self.client.library.history()
        for path in history:
            library_str = path.split("/")[-1]
            library_str = library_str.removesuffix(".library")
            self.library_path_dict[library_str] = path

        if self.library in self.library_path_dict:
            file_path = Path(self.library_path_dict[self.library]) / "metadata.json"
            if file_path.exists():
                return file_path
        raise ConnectionError(
            "Could not find metadata file for library %s", self.library
        )

    def parse_folder_dict(
        self, data: dict, parent_id: str
    ) -> tuple[str, list[Folder], list[Children]]:
        fid = ""
        name = ""
        folders = []
        relationships = []
        if data:
            fid = data["id"]
            name = data["name"]
            modification_time = decode_dt_ms(data["modificationTime"] / 1000.0)
            children = data["children"]
            folder = Folder(fid, name, modification_time)

            folders.append(folder)

            for child in children:
                child_id, sub_folders, sub_relationships = self.parse_folder_dict(
                    data=child, parent_id=fid
                )
                if child_id != "":
                    if sub_folders:
                        folders.extend(sub_folders)
                    rel = Children(fid, child_id)
                    relationships.append(rel)
                    if sub_relationships:
                        relationships.extend(sub_relationships)
        return fid, folders, relationships

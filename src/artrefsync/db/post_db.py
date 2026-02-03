from dataclasses import dataclass
import functools

import sqlite3
import os


from artrefsync.boards.board_handler import Post, PostFile
from artrefsync.config import config
from artrefsync.constants import APP, BOARD, DB, DB_TABLE, STORE, TABLE
from artrefsync.db.db_utils import BlobDb, DbUtils
from artrefsync.db.dataclass_db import Dataclass_DB

from artrefsync.utils.PyInstallerUtils import resource_path

import logging

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


class PostDb:
    # _instance = None
    # _context_depth = 0

    # def __new__(cls, *args, **kwargs):
    #     if cls._instance is None:
    #         cls._instance = super().__new__(cls)
    #     return cls._instance

    def __init__(
        self, connection: sqlite3.Connection | None = None, db_name=DB.TAGAPP_DB
    ):
        """Simple sqllite context manager to dump and load serialized (pickle) blob files
        Args:
            connection: Connection
            connection: sqlite3.Connection | None
            table_name_default: Default table name.
            db_name: If connection not provided this name will be used when creating a connection
        """
        self.connection = connection
        self.connection_owner = False
        if not self.connection:
            db_dir = resource_path(config[TABLE.APP][APP.DB_DIR])
            db_name = config[TABLE.APP][APP.DB_FILE_NAME]
            logger.debug("Creating connection with dir: %s, dbname: %s", db_dir, db_name)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
                db_name = os.path.join(db_dir, db_name)
            self.connection = sqlite3.connect(db_name)
            self.connection_owner = True
        self.commit = self.connection.commit

        self.posts = Dataclass_DB(Post, self.connection)
        self.files = Dataclass_DB(PostFile, self.connection)
        self.tag_posts = BlobDb(self.connection, "tagposts")
        self.artist_tags = BlobDb(self.connection, "artist_tag_counts")
        # self = BlobDb(self.connection, "tagposts")
        logger.debug("Opening PostDB")

    @functools.cached_property
    def board_artists(self) -> dict[str : list[str]]:
        board_artists_dict = {}
        select_result = self.posts.select([], ["DISTINCT artist_name, board"])
        for row in select_result:
            # pid = row["id"]
            board = row["board"]
            artist = row["artist_name"]
            if board not in board_artists_dict:
                board_artists_dict[board] = []
            board_artists_dict[board].append(artist)
        return board_artists_dict

    def get_tag_intersection(self, tags):
        posts = self.tag_posts.loads_blob(tags)
        if not posts:
            return set()
        if isinstance(tags, list) or isinstance(tags, set):
            if len(posts) == 1:
                return posts[0]
            else:
                return posts[0].intersection(*posts[1:])
        return posts

    def __enter__(self):
        logger.debug("PostDB Enter")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.connection.commit()
        logger.debug("Closing PostDB")
        self.connection.close()


def main():
    with PostDb() as db:
        for post in db.posts.select([("board", "danbooru")]):
            print(post.id)


if __name__ == "__main__":
    main()

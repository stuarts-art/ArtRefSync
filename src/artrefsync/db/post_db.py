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
    tables_initialized = False

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
            db_dir = config[TABLE.APP][APP.DB_DIR]
            db_name = config[TABLE.APP][APP.DB_FILE_NAME]
            logger.debug("Creating connection with dir: %s, dbname: %s", db_dir, db_name)
            if db_dir:
                db_name = resource_path(os.path.join(db_dir, db_name))
                os.makedirs(os.path.dirname(db_name), exist_ok=True)
            else:
                db_name = resource_path(db_name)
            logger.info("Creating or connecting to Database: %s", db_name)
            self.connection = sqlite3.connect(db_name)
            self.connection_owner = True
        self.commit = self.connection.commit
        if not self.tables_initialized:
            lazy = False
            self.tables_initialized = True
        else:
            lazy = True

        self.posts = Dataclass_DB(Post, self.connection, lazy = lazy)
        self.files = Dataclass_DB(PostFile, self.connection, lazy = lazy)
        self.tag_posts = BlobDb(self.connection, "tag_posts", lazy = lazy)
        self.artist_tags = BlobDb(self.connection, "artist_tags", lazy = lazy)
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
        
    def get_ids(self, board: BOARD = None, artist_name: str = None, db : Dataclass_DB = None):
        criteria = []
        if board:
            criteria.append(("board", board))
        if artist_name:
            criteria.append(("artist_name", artist_name))
        if not db:
            db = self.posts
        if not criteria:
            criteria = None
        
        return db.select_id_list(criteria)


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

if __name__ == "__main__":
    with PostDb() as db:
        db.files.select(None)



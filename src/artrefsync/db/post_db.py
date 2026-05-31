import logging
import os
import sqlite3

from artrefsync.utils.utils import resource_path
from artrefsync.db.TagType import ArtistTagCount, PostTagLink, Tag, TagType
from artrefsync.config import config
from artrefsync.db.db_utils import BlobDb, DbUtils
from artrefsync.db.dataclass_db import Dataclass_DB
from artrefsync.boards.board_handler import Post, PostFile
from artrefsync.constants import APP, BOARD, DB, TABLE
from artrefsync.utils.benchmark import Bm

logger = logging.getLogger(__name__)


def main():
    with PostDb(), Bm():
        pass

    with PostDb() as post_db, Bm():
        pass



class PostDb:
    tables_initialized = False

    def __init__(
        self, connection: sqlite3.Connection | None = None, db_dir = "", db_name = ""
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
            db_dir = db_dir if db_dir else config[TABLE.APP][APP.DB_DIR]
            db_name = db_name if db_name else config[TABLE.APP][APP.DB_FILE_NAME]
            if db_dir:
                db_name = resource_path(f"{db_dir}/{db_name}")
                os.makedirs(os.path.dirname(db_name), exist_ok=True)
            else:
                db_name = resource_path(db_name)
            logger.debug("Connecting to Database: %s", db_name)
            self.connection = sqlite3.connect(db_name)
            self.connection_owner = True
        self.commit = self.connection.commit
        if not PostDb.tables_initialized:
            lazy = False
            PostDb.tables_initialized = True
        else:
            lazy = True

        self.tags = Dataclass_DB(Tag, self.connection, lazy=lazy)
        self.posts = Dataclass_DB(Post, self.connection, lazy=lazy)
        self.files = Dataclass_DB(PostFile, self.connection, lazy=lazy)
        self.tag_types = Dataclass_DB(
            TagType, self.connection, lazy=lazy, key_list=["tag", "type"]
        )
        self.artist_tag_counts = Dataclass_DB(
            ArtistTagCount, self.connection, lazy=lazy, key_list=["artist", "tag"]
        )
        self.post_tag_link = Dataclass_DB(
            PostTagLink, self.connection, lazy=lazy, key_list=["pid", "tid"]
        )

        logger.debug("Opening PostDB")

    def update_tag_tables(self, pid, tags):
        post_row_id = self.posts.get_row_ids([pid,])[0]
        self.tags.insert_many([(tag,) for tag in tags])
        tag_row_ids = self.tags.get_row_ids(tags)
        query_args = tuple((post_row_id, tag_row_id) for tag_row_id in tag_row_ids)
        row_count = self.post_tag_link.insert_many(query_args)

    def select(
        self,
        select_args,
        from_args,
        join_str="",
        where_str="",
        suffix_str="",
        as_tupple=False,
        as_scalar=False,
    ):
        query = f"SELECT {select_args} FROM {from_args} {join_str} {where_str} {suffix_str};"
        logger.debug(query)
        cur = self.connection.cursor()
        if not as_tupple:
            cur.row_factory = DbUtils.dict_factory

        cur.execute(query)
        rows = cur.fetchall()
        if not rows:
            return []
        else:
            if as_tupple and as_scalar:
                return [row[0] for row in rows]
            return rows

    def get_last_id(self, artist, board):
        max_id = self.posts.select_freeform(
            select_args="ext_id, MAX(create_timestamp)",
            from_args="Post",
            where_str=f'WHERE board = "{board}" AND artist_name = "{artist}"',
            as_tupple=True,
        )
        return max_id[0][0]

    @property
    def board_artists(self) -> dict[str : list[str]]:
        board_artists_dict = {}
        select_result = self.posts.select([], ["DISTINCT artist_name", "board"])
        for row in select_result:
            # pid = row["id"]
            board = row["board"]
            artist = row["artist_name"]
            if board not in board_artists_dict:
                board_artists_dict[board] = []
            board_artists_dict[board].append(artist)
        return board_artists_dict

    def get_ids(
        self, board: BOARD = None, artist_name: str = None, db: Dataclass_DB = None
    ):
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


    def get_missing_post_file_ids(self):
        missing_ids = self.posts.select_freeform(
            select_args="t1.id",
            from_args=f"{Post.__name__} t1",
            join_str=f"LEFT JOIN {PostFile.__name__} t2 ON t1.id = t2.id",
            where_str="WHERE t2.id IS NULL",
            as_tupple=True,
            as_scalar=True,
        )
        return missing_ids

    def get_posts_with_files(self):
        missing_ids = self.posts.select_freeform(
            select_args="t1.id, t1.artist_name, t1.board",
            from_args=f"{Post.__name__} t1",
            join_str=f"LEFT JOIN {PostFile.__name__} t2 ON t1.id = t2.id",
            where_str="WHERE t2.id IS NULL",
        )
        return missing_ids

    def tags_from_post(self, pid):
        query = [
            "SELECT t1.tag",
            "FROM PostTagLink pt",
            f"JOIN {Post.__name__} p1 ON pt.pid = p1.rowid",
            f"JOIN {Tag.__name__} t1 ON  pt.tid = t1.rowid",
            "WHERE p1.id = ?",
        ]
        query_str = " ".join(query)
        cur = self.connection.cursor()
        cur.row_factory = DbUtils.scalor_row_factory
        cur.execute(query_str, (pid,))
        rows = cur.fetchall()
        return rows

    def posts_from_tag(self, tag, as_count=False, order_by="id", order_dir="DESC"):
        query = [
            "SELECT",
            "COUNT(*)" if as_count else "p1.id",
            "FROM PostTagLink pt",
            f"JOIN {Post.__name__} p1 ON pt.pid = p1.rowid",
            f"JOIN {Tag.__name__} t1 ON  pt.tid = t1.rowid",
            "WHERE t1.tag = ?",
            "" if as_count else f"ORDER BY {order_by} {order_dir}",
        ]
        query_str = " ".join(query)
        cur = self.connection.cursor()
        cur.row_factory = DbUtils.scalor_row_factory
        cur.execute(query_str, (tag,))
        rows = cur.fetchall()
        if as_count:
            return rows[0] if rows else 0
        return rows

    def posts_by_artist(self):
        query = [
            "SELECT",
            "t1.tag, count(p1.id)as count",
            "FROM PostTagLink pt",
            f"JOIN {Post.__name__} p1 ON pt.pid = p1.rowid",
            f"JOIN {Tag.__name__} t1 ON  pt.tid = t1.rowid",
            "WHERE t1.tag IN",
            f"(SELECT t2.tag FROM {TagType.__name__} t2 WHERE t2.type = \"artist\")",
            # f"JOIN {TagType.__name__} t2 ON  t1.tag=t2.tag",
            "group by t1.tag",
            "ORDER BY count DESC"
        ]
        query = [
            "SELECT p1.id, count(t1.tag) as count",
            "FROM PostTagLink pt",
            f"JOIN {Post.__name__} p1 ON pt.pid = p1.rowid",
            f"JOIN {Tag.__name__} t1 ON  pt.tid = t1.rowid",
            "WHERE pt.tid IN ",
            "(",
            f"SELECT t1.rowid FROM {TagType.__name__} t2",
            f"JOIN {Tag.__name__} t1 ON  t2.tag = t1.tag",
            "WHERE t2.type = \"artist\"",
            ")",
            "GROUP BY p1.id",
            "ORDER BY count desc"
        ]
        query_str = " ".join(query)
        cur = self.connection.cursor()
        cur.execute(query_str)
        rows = cur.fetchall()
        return rows

    def post_counts_for_tags(self, tags:list[str]):
        query = [
            "SELECT",
            "t1.tag, COUNT(*)",
            "FROM PostTagLink pt",
            f"JOIN {Post.__name__} p1 ON pt.pid = p1.rowid",
            f"JOIN {Tag.__name__} t1 ON  pt.tid = t1.rowid",
            f"WHERE t1.tag IN ('{"', '".join(tags)}')",
            "GROUP BY t1.tag"
        ]
        query_str = " ".join(query)
        cur = self.connection.cursor()
        cur.execute(query_str)
        rows = cur.fetchall()

        counts = {k:v for (k, v) in rows}
        return counts

    def posts_in_intersection(self, tags =[], order_by="id", order_dir="DESC", limit = 100, offset = 0, as_count = False):
        if isinstance(tags, str):
            tags = [tags]
        if not tags:
            query = [
                "SELECT",
                "count(pf.id)" if as_count else "pf.id",
                f"FROM {PostFile.__name__} pf",
                f"JOIN {Post.__name__} p1 ON pf.id = p1.id",
                f"ORDER BY p1.{order_by} {order_dir}" if order_by else "",
                f"LIMIT {limit} OFFSET {offset}" if not as_count else ""
            ]
        # elif len(tags) == 1:
        #     return self.posts_from_tag(tags[0], order_by=order_by, order_dir=order_dir)
        else:
            query = [
                "SELECT",
                "count(pf1.id)" if as_count else "pf1.id",
                "FROM PostTagLink pt",
                f"JOIN {Post.__name__} p1 ON pt.pid = p1.rowid",
                f"JOIN {PostFile.__name__} pf1 ON p1.id = pf1.id",
                f"JOIN {Tag.__name__} t1 ON  pt.tid = t1.rowid",
                f"WHERE t1.tag IN ('{"', '".join(tags)}')",
                "GROUP BY pf1.id" if not as_count else "",
                f"HAVING COUNT(DISTINCT t1.tag) = {len(tags)}",
                f"ORDER BY p1.{order_by} {order_dir}" if order_by else "",
                f"LIMIT {limit} OFFSET {offset}" if not as_count else ""
            ]
        query_str = " ".join(query)
        cur = self.connection.cursor()
        cur.row_factory = DbUtils.scalor_row_factory
        cur.execute(query_str)
        rows = cur.fetchall()
        # if as_count:
        #     return rows[0] if rows else 0
        return rows

    def get_tag_counts(
        self, artist="", search="", type="", as_tupple=True, limit=1000, offset=0
    ):

        select_args = "t1.tag as tag, t1.count as count"
        from_args = "ArtistTagCount as t1"
        join_str = ""
        suffix_str = ""
        conditions = []

        if artist != "":
            conditions.append(f't1.artist = "{artist}"')
        else:
            # Handle No Artist:
            select_args = "t1.tag as tag, SUM(t1.count) as count"
            suffix_str = "GROUP BY t1.tag"
            conditions.append("t1.artist in ('e621', 'danbooru', 'r34')")

        if search != "":
            conditions.append(f't1.tag LIKE "%{search}%"')

        if type != "":
            # select_args += ", t2.type"
            join_str = "INNER JOIN TagType as t2 ON t1.tag = t2.tag"
            conditions.append(f't2.type = "{type}"')

        suffix_str += " ORDER BY count DESC"
        if limit:
            suffix_str += f" LIMIT {limit}"

        if offset:
            suffix_str += f" OFFSET {offset}"
        where_str = f"WHERE {' AND '.join(conditions)}"

        tag_counts = self.artist_tag_counts.select_freeform(
            select_args=select_args,
            from_args=from_args,
            join_str=join_str,
            where_str=where_str,
            suffix_str=suffix_str,
            as_tupple=as_tupple,
        )

        return tag_counts

    def __enter__(self):
        logger.debug("PostDB Enter")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.connection.commit()
        logger.debug("Closing PostDB")
        self.connection.close()


if __name__ == "__main__":
    main()

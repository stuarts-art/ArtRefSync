import functools
import logging
import os
import sqlite3

from dataclassdb import DataclassDb, QueryBuilder
from tenacity import retry, stop_after_attempt

from artrefsync.boards.board_models import Post
from artrefsync.config import get_config
from artrefsync.constants import APP, BOARD, DANBOORU, E621, R34, TABLE
from artrefsync.db.db_models import ArtistTagCount, PostTagLink, Tag, TagType
from artrefsync.stores.store_models import PostFile

config = get_config()
logger = logging.getLogger(__name__)


class PostDb:
    def __enter__(self):
        logger.debug("PostDB Enter")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.connection.commit()
        logger.debug("Closing PostDB")
        self.connection.close()

    tables_initialized = False

    def __init__(
        self, connection: sqlite3.Connection | None = None, db_dir="", db_name=""
    ):
        """Temp Class to shadow PostDb until migration to dataclassdb is complete.

        Args:
            connection (sqlite3.Connection | None, optional): _description_. Defaults to None.
            db_dir (str, optional): _description_. Defaults to "".
            db_name (str, optional): _description_. Defaults to "".

        Returns:
            _type_: _description_
        """
        self.connection = connection
        self.connection_owner = False
        if not self.connection:
            db_dir = db_dir if db_dir else config[TABLE.APP][APP.DB_DIR]
            db_name = db_name if db_name else config[TABLE.APP][APP.DB_FILE_NAME]

            if db_dir:
                db_file_name = config.resource_path(f"{db_dir}/{db_name}")
                os.makedirs(os.path.dirname(db_file_name), exist_ok=True)
            else:
                db_file_name = config.resource_path(db_name)
            logger.debug("Connecting to Database: %s", db_file_name)
            self.connection = sqlite3.connect(db_file_name)
            self.connection_owner = True
        self.commit = self.connection.commit
        if not PostDb.tables_initialized:
            verify_table = True
            PostDb.tables_initialized = True
        else:
            verify_table = False

        self.tags = DataclassDb(Tag, self.connection, verify_table=verify_table)
        self.posts = DataclassDb(Post, self.connection, verify_table=verify_table)
        self.files = DataclassDb(PostFile, self.connection, verify_table=verify_table)
        self.tag_types = DataclassDb(
            TagType, self.connection, verify_table=verify_table
        )
        self.artist_tag_counts = DataclassDb(
            ArtistTagCount, self.connection, verify_table=verify_table
        )
        self.post_tag_link = DataclassDb(
            PostTagLink, self.connection, verify_table=verify_table
        )

        self.posts.CREATE.INDEX.IF.NOT.EXISTS("post_id_index").ON(Post).par(
            "id"
        ).execute()
        self.posts.CREATE.INDEX.IF.NOT.EXISTS("post_artist_index").ON(Post).par(
            "artist_name"
        ).execute()
        self.files.CREATE.INDEX.IF.NOT.EXISTS("postfile_artist_index").ON(Post).par(
            "artist_name"
        ).execute()

    @retry(stop=stop_after_attempt(3))
    def update_tag_link_table(self, post_sql_id, tags):
        tag_ids = [self.tags.insert(Tag(tag)) for tag in tags]
        if tag_ids:
            self.post_tag_link.insert_many(
                [PostTagLink(post_id=post_sql_id, tag_id=tag_id) for tag_id in tag_ids]
            )

    @retry(stop=stop_after_attempt(3))
    def update_tag_types(self, tags, type_):
        tag_ids = [self.get_tag_id(tag) for tag in tags]
        tag_types = [TagType(tag_id=tag_id, type=type_) for tag_id in tag_ids]
        for tag_type in tag_types:
            self.tag_types.insert(tag_type)

    @functools.lru_cache  # noqa: B019
    @retry(stop=stop_after_attempt(3))
    def get_tag_id(self, tag: str):
        return self.tags.insert(Tag(tag))

    @retry(stop=stop_after_attempt(3))
    def get_board_artists(self) -> dict[str, dict[str, int]]:
        board_artist_count: dict[str, dict[str, int]] = {}

        for board in [TABLE.E621, TABLE.R34, TABLE.DANBOORU]:
            board_artist_count[board] = {}
            artist_list = config[board]["artists"]
            for artist in artist_list:
                board_artist_count[board][artist] = 0

            with QueryBuilder(self.connection) as qb:
                qb.SELECT("tag", "count").FROM(ArtistTagCount)
                qb.WHERE("artist").eq(board, quotes=True)
                qb.AND("tag").IN.placeholders(*artist_list)
                artist_count_list = qb.execute()
            for artist, count in artist_count_list:
                board_artist_count[board][artist] = count
        return board_artist_count

    @retry(stop=stop_after_attempt(3))
    def post_counts_for_tags(self, tags: list[str]):
        query = QueryBuilder().select("t1.tag", "COUNT(*)").from_(PostTagLink, "pt")
        query.join(Post, "p1", "pt.post_id = p1.sql_id")
        query.join(Tag, "t1", "pt.tag_id = t1.sql_id")
        query.WHERE("t1.tag").IN.placeholders(*tags, par=True)
        query.GROUP.BY("t1.tag")

        rows = self.post_tag_link.execute(*tags, sql_str=str(query), as_dict=False)

        counts = {k: v for (k, v) in rows}
        return counts

    @retry(stop=stop_after_attempt(3))
    def get_tag_counts(
        self, artist="", search="", type_="", as_tuple=True, limit=0, offset=0
    ):
        query = QueryBuilder(self.artist_tag_counts.connection)
        params = []
        conditions = []

        if artist:
            query.SELECT("at1.tag as tag", "at1.count as count").from_(
                ArtistTagCount, "at1"
            )
            conditions.append("at1.artist = ?")
            params.append(artist)
        else:
            query.SELECT("at1.tag as tag", "SUM(at1.count) as count").from_(
                ArtistTagCount, "at1"
            )
            conditions.append("at1.artist IN (?, ?, ?)")
            params.extend(["e621", "r34", "danbooru"])

        if search:
            conditions.append("at1.tag LIKE ?")
            params.append(f"%{search}%")

        if type_:
            query.join(Tag, "t1", "at1.tag = t1.tag", join_type="INNER")
            query.join(TagType, "tt1", "t1.sql_id = tt1.tag_id", join_type="INNER")
            conditions.append("tt1.type = ?")
            params.append(type_)

        query.WHERE(" AND ".join(conditions))
        query.GROUP.BY("at1.tag")

        query.ORDER.BY("count").DESC  # noqa: B018

        if limit:
            query.LIMIT("?")
            params.append(limit)

            if offset:
                query.OFFSET(offset)
                params.append(offset)

        tag_counts = query.execute(*params, as_dict=not as_tuple)

        return tag_counts

    def update_artist_tag_count(self, artist):
        if not artist:
            logger.info("Artist %s has no tag counts.", artist)
            return
        with QueryBuilder(self.connection) as qb:
            qb.BEGIN.TRANSACTION.end()
            qb.DELETE.FROM(ArtistTagCount).WHERE("artist").eq.quote(artist).end()
            qb.INSERT.INTO(ArtistTagCount).par("artist", "tag", "count")
            qb.SELECT(f'"{artist}"', "t.tag", "count(*) AS count")
            qb.from_(PostTagLink, "pt")
            qb.join(Tag, "t", "t.sql_id = pt.tag_id")
            qb.join(Post, "p", "p.sql_id = pt.post_id")
            qb.WHERE("p.artist_name").eq.quote(artist)
            qb.GROUP.BY("p.artist_name", "t.tag").end()
            qb.END.TRANSACTION.end()
            qb.execute_script()

    def update_board_tag_counts(self, board):

        if not board:
            logger.warning("Update board tag counts called without board")
            return
        artist_list = config[board]["artists"]

        with QueryBuilder(self.connection) as qb:
            qb.BEGIN.TRANSACTION.end()
            qb.DELETE.FROM(ArtistTagCount).WHERE("artist").eq.quote(board).end()
            qb.INSERT.INTO(ArtistTagCount).par("artist", "tag", "count")
            qb.SELECT(f'"{board}"', "tag", "SUM(count) as count")
            qb.FROM(ArtistTagCount)
            qb.WHERE("artist").IN.quote(*artist_list, par=True)
            qb.GROUP.BY("tag").end()
            qb.END.TRANSACTION.end()
            qb.execute_script()

    @retry(stop=stop_after_attempt(3))
    def posts_in_intersection(
        self,
        tags: list[str] | None = None,
        order_by="id",
        order_dir="DESC",
        limit=100000,
        offset=0,
        as_count=False,
    ):
        if tags is None:
            tags = []
        if isinstance(tags, str):
            tags = [tags]

        query = QueryBuilder(self.connection)
        params = []
        if not tags:
            if as_count:
                query.SELECT("pf.id")
            else:
                query.SELECT("pf.id")
            query.from_(PostFile, "pf")
            query.join(Post, "p1", "pf.id = p1.id")

        else:
            if as_count:
                query.SELECT("COUNT(DISTINCT pf.id) AS count")
            else:
                query.SELECT("pf.id")

            query.from_(PostTagLink, "pt")
            query.join(Post, "p1", "pt.post_id = p1.sql_id", join_type="INNER")
            query.join(PostFile, "pf", "p1.id = pf.id", join_type="INNER")
            query.join(Tag, "t1", "pt.tag_id = t1.sql_id", join_type="INNER")
            query.WHERE("t1.tag").IN(["?"] * len(tags), par=True)
            params.extend(tags)
            query.GROUP.BY("pf.id")
            query.HAVING.Count("DISTINCT t1.tag").eq(len(tags))

        if as_count:
            subquery_name = "intersection_rows"
            temp_query = query.as_string()
            query.WITH(subquery_name).AS(temp_query, par=True).SELECT("COUNT(*)").FROM(
                subquery_name
            )
        else:
            if order_by:
                query.ORDER.BY(f"p1.{order_by} {order_dir}")
            if limit:
                query.LIMIT(limit).OFFSET(offset)

        rows = query.execute(*params, as_dict=False)
        if as_count:
            return rows[0][0]
        else:
            return [row[0] for row in rows]

    def remove_black_listed_posts(self, board):
        black_list = config[board]["black_list"]
        logger.info("Removing black listed posts for board %s", board)
        with QueryBuilder(self.connection) as qb:
            qb.SELECT("DISTINCT pt.post_id", "p.id")
            qb.from_(PostTagLink, "pt")
            qb.join(Tag, "t", "t.sql_id = pt.tag_id")
            qb.join(Post, "p", "p.sql_id = pt.post_id")
            qb.WHERE("t.tag").IN.quote(*black_list, par=True)
            qb.AND("p.board").eq.quote(board)
            result = qb.execute()

        if not result:
            logger.info("Black list empty")
            return

        sql_ids, ids = zip(*result)
        with QueryBuilder(self.connection) as qb:
            qb.BEGIN.TRANSACTION.end()
            qb.DELETE.FROM(PostTagLink).WHERE("post_id").IN.quote(
                *sql_ids, par=True
            ).end()
            qb.DELETE.FROM(Post).WHERE("sql_id").IN.quote(*sql_ids, par=True).end()
            qb.DELETE.FROM(PostFile).WHERE("id").IN.quote(*ids, par=True).end()
            qb.END.TRANSACTION.end()
            qb.execute_script()

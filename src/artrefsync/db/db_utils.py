from collections.abc import Iterable
import sqlite3
import pickle
import time

from artrefsync.utils.benchmark import Bm
import logging

logger = logging.getLogger()


class DbUtils:
    @staticmethod
    def table_exists(connection: sqlite3.Connection, table_name):
        cursor = connection.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        result = cursor.fetchone()
        return result is not None

    # @staticmethod
    # def table_columns(connection: sqlite3.Connection, table_name):
    #     cursor = connection.cursor()
    #     cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
    #     columns = [description[0] for description in cursor.description]
    #     return columns

    @staticmethod
    def dict_factory(cursor, row):
        # return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
        return {
            col[0]: (
                pickle.loads(row[idx]) if isinstance(row[idx], bytes) else row[idx]
            )
            for idx, col in enumerate(cursor.description)
        }

    @staticmethod
    def placeholder(count):
        return ", ".join("?" * count)

    @staticmethod
    def table_columns(connection: sqlite3.Connection, table_name):
        cursor = connection.cursor()
        cursor.execute(f"PRAGMA table_info('{table_name}')")
        result = cursor.fetchall()
        if result:
            return [row[1] for row in result]
        return None


class BlobDb:
    def __init__(
        self,
        connection: sqlite3.Connection | None = None,
        table_name_default="blob_table",
        db_name="blob.db",
        count_field=False,
    ):
        """
        Simple sqllite context manager to dump and load serialized (pickle) blob files

        :param connection: Connection
        :type connection: sqlite3.Connection | None
        :param table_name_default: Default table name.
        :param db_name: If connection not provided this name will be used when creating a connection
        """

        self.count_field = count_field

        self.connection = connection
        self.connection_owner = False
        if not self.connection:
            self.connection = sqlite3.connect(db_name)
            self.connection_owner = True
        self.loaded_tables = set()
        self.table_name_default = table_name_default
        self.commit = self.connection.commit
        self.primary_key = "id"

        self.cols = ["id", "data", "count", "updatetime"]
        self.create_if_missing(self.table_name_default)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.connection.commit()
        if self.connection_owner:
            self.connection.close()
        pass

    def create_if_missing(self, table_name):
        create_table = False
        cursor = self.connection.cursor()
        if table_name not in self.loaded_tables:
            if not DbUtils.table_exists(self.connection, table_name):
                create_table = True
            else:
                existing_cols = DbUtils.table_columns(
                    self.connection, self.table_name_default
                )
                if existing_cols != self.cols:
                    create_table = True
        if create_table:
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            cursor.execute(
                f"CREATE TABLE {table_name} (id TEXT PRIMARY KEY, data BLOB, count INTEGER, updatetime INTEGER)"
            )
            self.loaded_tables.add(table_name)

    def dumps_blob(self, key, object, table_name=None):
        count = 0
        if hasattr(object, "__len__"):
            count = len(object)

        if table_name:
            self.create_if_missing(table_name)
        table_name = table_name if table_name else self.table_name_default

        cursor = self.connection.cursor()
        cursor.execute(
            f"INSERT OR REPLACE INTO {table_name} (id, data, count, updatetime) VALUES (?, ?, ?, ?)",
            (key, pickle.dumps(object), count, int(time.time())),
        )

    def loads_blob(
        self, key: int | str | float | Iterable, max_age_seconds=0, table_name=None
    ):
        if table_name:
            self.create_if_missing(table_name)
        table_name = table_name if table_name else self.table_name_default
        cursor = self.connection.cursor()
        time_suffix = ""
        if max_age_seconds:
            time_suffix = f" AND {int(time.time())}-updatetime < {max_age_seconds}"

        if isinstance(key, list) or isinstance(key, set):
            key = list(key)  # explicitly cast to list incase of set.
            query = f"SELECT data FROM {table_name}  WHERE (id) IN ({', '.join('?' * len(key))}){time_suffix};"
            cursor.execute(query, key)
            fetch = cursor.fetchall()
            if fetch:
                return [pickle.loads(row[0]) for row in fetch]
            else:
                return None
        else:
            cursor.execute(
                f"SELECT data FROM {table_name}  WHERE (id) = (?){time_suffix};", (key,)
            )
            fetch = cursor.fetchone()
            if fetch:
                return pickle.loads(fetch[0])
            else:
                return None

    def count(self, key):
        query = f"SELECT count FROM {self.table_name_default} WHERE {self.primary_key} = ? LIMIT 1"
        cur = self.connection.cursor()
        cur.execute(query, (key,))
        result = cur.fetchone()
        # print(f" QUERY RESULT for key {key} - {result}")
        if result and len(result) == 1:
            return result[0]
        else:
            return 0

    def count_list(self, starts_with=None, limit=100, count_order="DESC"):
        if starts_with:
            query = f"SELECT id, count FROM {self.table_name_default} WHERE {self.primary_key} LIKE ? ORDER BY count DESC LIMIT ?"
            cur = self.connection.cursor()
            cur.execute(query, (f"%{starts_with}%", limit))
        else:
            query = f"SELECT id, count FROM {self.table_name_default} ORDER BY count DESC LIMIT ?"
            cur = self.connection.cursor()
            cur.execute(query, (limit,))

        result = cur.fetchall()
        logger.debug(f" QUERY RESULT for key {starts_with} - {result}")
        if result:
            # result = sorted(result, key=lambda item: int(item[1]), reverse=True)
            return result
        else:
            return []

    def union_update(self, key, input_set: set):
        """If the picked object is a set, union it and replace the value.

        PARAMS:
        key: Table Key
        input_set: Input set to union on
        """
        current_set: set = self.loads_blob(key)
        if current_set:
            if not isinstance(current_set, set):
                raise TypeError(
                    f"Union Update called in Blob DB on a Non-Set type {type(current_set)} for key {key}"
                )
            new_set = current_set.union(input_set)
            if len(current_set) == len(new_set):
                return current_set
            else:
                self.dumps_blob(key, new_set)
            return new_set
        else:
            self.dumps_blob(key, input_set)
            return input_set

    def __contains__(self, key) -> bool:
        # key in db
        query = f"SELECT 1 FROM {self.table_name_default} WHERE {self.primary_key} = ? LIMIT 1"
        cur = self.connection.cursor()
        cur.execute(query, (key,))
        result = cur.fetchone()
        return result is not None

    def __getitem__(self, key):
        return self.loads_blob(key)


if __name__ == "__main__":
    s = set([1, 2, 3, 4, 5])
    with BlobDb(db_name="testing.db") as blob_db:
        blob_db.dumps_blob("test1", s)
        blob_db.dumps_blob("test2", [6, 7, 8])
        blob_db.dumps_blob("test3", [6, 7, 8, 0, 19, 390])

        with Bm():
            print(blob_db.count("test"))
            print(blob_db.count_list("te"))

from collections.abc import Iterable
import logging
import pickle
import sqlite3
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Generic, Type, TypeVar

import dacite

from artrefsync.db.db_utils import DbUtils
from artrefsync.config import config

T = TypeVar("T", contravariant=dataclass)


class Dataclass_DB(Generic[T]):
    def __init__(
        self,
        cls: Type[T],
        connection: sqlite3.Connection | None = None,
        table_name=None,
        db_name=None,
        lazy=False,
    ):
        """Stripped down sqlite dataclass connector
        Args:
            connection: Connection - If no connection given, create one.
            table_name_default: Default table name. - Table to create for a given dataclass
            db_name: Overridable database name. If not given, name db after dataclass.
            * This class does not automatically commit on each transaction.
        """
        self.logger = logging.getLogger(cls.__name__)
        self.logger.setLevel(config.log_level)
        self.cls = cls
        self.connection = connection
        self.connection_owner = False
        self.table_name = table_name if table_name else cls.__name__
        self.db_name = (
            db_name
            if db_name
            else DbUtils.resource_path(cls.__name__ + "_dataclassdb.db")
        )
        if not self.connection:
            self.logger.info("Creating or connecting to Database: %s", self.db_name)
            self.connection = sqlite3.connect(self.db_name)
            self.connection_owner = True
        self.commit = self.connection.commit
        self.field_types, self.table_fields, self.primary_key = DbUtils.get_sql_fields(
            cls
        )
        if not lazy:
            self.create_or_update_table(cls)

    def create_or_update_table(self, cls):
        self.logger.info("Creating table for class %s", cls)
        cur = self.connection.cursor()
        create_table_flag = False
        drop_table_flag = False

        if DbUtils.table_exists(self.connection, self.table_name):
            existing_cols = DbUtils.table_columns(self.connection, self.table_name)
            for i, (field, type) in enumerate(self.field_types.items()):
                table_field = self.table_fields[i]
                if field not in existing_cols:
                    if "PRIMARY KEY" in table_field or "UNIQUE" in table_field:
                        drop_table_flag = True
                        create_table_flag = True
                        break

                    query = f"ALTER TABLE {self.table_name} ADD COLUMN {self.table_fields[i]};"
                    self.logger.warning(
                        "Adding field %s to table %s with query: %s",
                        field,
                        self.table_name,
                        query,
                    )
                    cur.execute(query)
                elif type != existing_cols[field]:
                    drop_table_flag = True
                    create_table_flag = True
                    break
        else:
            create_table_flag = True

        if drop_table_flag:
            query = f"DROP TABLE {self.table_name}"
            self.logger.warning(
                "Unsupported field modification. Dropping, then remaking table.",
                field,
                self.table_name,
                query,
            )
            cur.execute(query)

        if create_table_flag:
            query = f"CREATE TABLE IF NOT EXISTS {self.table_name} (\n{',\n'.join(self.table_fields)}\n);"
            self.logger.debug('Creating Table with Query "%s"', query)
            cur.execute(query)
            self.commit()

            auto_update_query = f"""
                CREATE TRIGGER IF NOT EXISTS update_{self.table_name}_updated
                AFTER UPDATE ON {self.table_name}
                WHEN old.updated <> strftime('%s', 'now')
                BEGIN
                    UPDATE {self.table_name}
                    SET updated = strftime('%s', 'now')
                    WHERE {self.primary_key} = OLD.{self.primary_key};
                END;
            """
            cur.execute(auto_update_query)
            self.commit()

    def insert(self, item: T):
        """
        If the item does not exist, insert, else replace.
        Returns True if inserted, false if updated.
        """
        item_dict = asdict(item)
        exists = str(item_dict[self.primary_key]) in self
        query_values = tuple(
            pickle.dumps(kv[1]) if self.field_types[kv[0]] == "BLOB" else kv[1]
            for kv in item_dict.items()
            if kv[0] in self.field_types
        )
        field_names: str = ", ".join([k for k in self.field_types])
        placeholders = DbUtils.placeholder(len(self.field_types))
        query = f"INSERT OR REPLACE INTO {self.table_name} ({field_names}) VALUES({placeholders})"

        cur = self.connection.cursor()
        cur.execute(query, query_values)
        return not exists

    def get_all(
        self,
        id_list=list[str],
        select_fields=None,
        as_tupple=False,
        as_scalar=False,
        suffix="",
    ) -> list[T]:
        """
        id_list: list of ids to query from.
        select_fields: fields to get
        as_tupple: returns tupple of values instead of dict or class
        as_scalar: returns list of ids. Overrides selected_fields, as_tupple
        suffix: suffix to append to query

        """
        if isinstance(id_list, Iterable):
            id_list = tuple(id_list)
        else:
            id_list = tuple(
                id,
            )

        if as_scalar:
            select_fields = [
                "id",
            ]
            as_tupple = True

        field_str = "*" if not select_fields else ", ".join(select_fields)

        query = f"SELECT {field_str} FROM {self.table_name}  WHERE (id) IN ({', '.join('?' * len(id_list))}) {suffix}"
        cur = self.connection.cursor()
        if not as_tupple:
            cur.row_factory = DbUtils.dict_factory
        cur.execute(query, tuple(id_list))
        rows = cur.fetchall()

        if not rows:
            return None
        elif as_scalar:
            return [row[0] for row in rows]

        elif as_tupple or select_fields:
            return rows
        else:
            return [
                dacite.from_dict(self.cls, row, config=dacite.Config(cast=[StrEnum]))
                for row in rows
            ]

    def get(self, item_id: str, select_fields: list[str] = None, as_tupple=False) -> T:
        field_str = "*" if not select_fields else ", ".join(select_fields)
        query = f"SELECT {field_str} FROM {self.table_name}  WHERE (id) = ?"
        cur = self.connection.cursor()
        if not as_tupple:
            cur.row_factory = DbUtils.dict_factory
        cur.execute(query, (item_id,))
        item = cur.fetchone()

        if not item:
            return None
        elif as_tupple:
            return item
        elif select_fields:
            return item
        else:
            return dacite.from_dict(
                self.cls, item, config=dacite.Config(cast=[StrEnum])
            )

    def select(
        self, conditions: list[tuple] = [], select_fields: list[str] = None, suffix=""
    ) -> list[T]:
        if conditions:
            condition_fields, condition_vals = zip(*conditions)
            condition_query_str = " WHERE " + " AND ".join(
                [f"{x} = ?" for x in condition_fields]
            )
        else:
            condition_vals = None
            condition_query_str = ""

        has_select_fields = select_fields is not None
        select_fields = "*" if not select_fields else ", ".join(select_fields)
        query = f"SELECT {select_fields} FROM {self.table_name}{condition_query_str}{suffix}"

        cur = self.connection.cursor()
        cur.row_factory = DbUtils.dict_factory

        if condition_vals:
            cur.execute(query, (*condition_vals,))
        else:
            cur.execute(query)
        items = cur.fetchall()

        if has_select_fields:
            return items
        elif not items:
            return []
        else:
            return [
                dacite.from_dict(self.cls, item, config=dacite.Config(cast=[StrEnum]))
                for item in items
            ]

    def select_id_list(self, conditions: list[tuple], suffix="") -> list[T]:
        if conditions:
            condition_fields, condition_vals = zip(*conditions)
            condition_query_str = " WHERE " + " AND ".join(
                [f"{x} = ?" for x in condition_fields]
            )
        else:
            condition_vals = None
            condition_query_str = ""
        select_fields = self.primary_key
        query = f"SELECT {select_fields} FROM {self.table_name}{condition_query_str}{suffix}"
        cur = self.connection.cursor()

        if condition_vals:
            cur.execute(query, (*condition_vals,))
        else:
            cur.execute(query)
        items = cur.fetchall()
        return [row[0] for row in items]

    def update(self, item_id: str, item: T, item_fields: list[str] = None):
        """Update list of fields. If no item field is given, replace the item."""
        if not item_fields:
            return self.insert(item)

        field_names = ", ".join(f"{item_f} = ?" for item_f in item_fields)
        query = f"UPDATE {self.table_name} SET {field_names} WHERE id = ?"
        query_values = tuple(
            pickle.dumps(kv[1]) if self.field_types[kv[0]] == "BLOB" else kv[1]
            for kv in asdict(item).items()
            if kv[0] in item_fields
        )
        cur = self.connection.cursor()
        cur.row_factory = DbUtils.dict_factory
        cur.execute(query, query_values + (item_id,))

    def update_fields(self, item_id: str, item_field_values: list[tuple[str, str]]):
        """Update list of fields. If no item field is given, replace the item."""

        field_names = ", ".join(f"{ifield} = ?" for ifield, _ in item_field_values)
        query_values = tuple(
            pickle.dumps(ivalue) if self.field_types[ifield] == "BLOB" else ivalue
            for ifield, ivalue in item_field_values
        )
        query = f"UPDATE {self.table_name} SET {field_names} WHERE id = ?"
        cur = self.connection.cursor()
        cur.row_factory = DbUtils.dict_factory
        cur.execute(query, query_values + (item_id,))

    def __contains__(self, key) -> bool:
        query = f"SELECT 1 FROM {self.table_name} WHERE {self.primary_key} = ? LIMIT 1"
        cur = self.connection.cursor()
        cur.execute(query, (key,))
        result = cur.fetchone()
        return result is not None

    def __getitem__(self, key) -> T:
        return self.get(key)

    def __setitem__(self, key, value) -> T:
        setattr(value, self.primary_key, key)
        self.insert(value)

    def __len__(self) -> int:
        query = f"SELECT COUNT(*) FROM {self.table_name};"
        cur = self.connection.cursor()
        cur.execute(query)
        result = cur.fetchone()
        return result[0]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.connection.commit()
        if self.connection_owner:
            self.connection.close()
        pass

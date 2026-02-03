from enum import StrEnum
import logging
import sqlite3
from types import NoneType, UnionType

import dacite
from artrefsync.boards.board_handler import Post, PostFile
from typing import Generic, Literal, TypeVar, List, Type, get_type_hints
from dataclasses import dataclass, astuple, asdict, fields
import pickle
from artrefsync.constants import BOARD
from artrefsync.db.db_utils import DbUtils

T = TypeVar("T", contravariant=dataclass)



class Dataclass_DB(Generic[T]):
    field_type_map = {}
    primary_key_map = {}

    def __init__(self, cls: Type[T], connection: sqlite3.Connection|None = None, table_name = None, db_name = None):
        self.logger = logging.getLogger(cls.__name__)
        """ Stripped down sqlite dataclass connector
        Args:
            connection: Connection - If no connection given, create one.
            table_name_default: Default table name. - Table to create for a given dataclass
            db_name: Overridable database name. If not given, name db after dataclass.
            * This class does not automatically commit on each transaction.
        """
        self.cls = cls
        self.connection = connection
        self.connection_owner = False
        self.table_name = table_name if table_name else cls.__name__
        self.db_name = db_name if db_name else cls.__name__ +"_dataclassdb.db"
        if not self.connection:
            self.connection = sqlite3.connect(self.db_name)
            self.connection_owner = True
        self.commit = self.connection.commit

        if cls in self.field_type_map:
            self.field_type = self.field_type_map[cls] 
            self.primary_key = self.primary_key_map[cls] 
            return

        _type_map = {str: "TEXT", StrEnum: "TEXT", int: "INTEGER", float: "REAL"}

        self.field_type = {}
        self.primary_key = ""
        # annotations = cls.__annotations__.items()
        annotations = get_type_hints(cls).items()
        existing_cols = []

        if DbUtils.table_exists(self.connection, self.table_name):
            existing_cols = DbUtils.table_columns(self.connection, self.table_name)            

        table_fields = []
        for i, (annotation , ann_field) in enumerate(annotations):
            types = list(ann_field.__args__) if isinstance(ann_field, UnionType) else [ann_field,]
            self.logger.debug(types)
            field_sql_type = "BLOB"

            # Set Suffix
            if i == 0:
                self.primary_key = annotation
                field_suffix = " PRIMARY KEY"
            else:
                field_suffix = " NOT NULL" if NoneType not in types else ""

            # Determine Field type
            for sql_type_field, sql_type_str in _type_map.items():
                for type in types:
                    
                    if issubclass(type, sql_type_field):
                        field_sql_type = sql_type_str
                        break
            self.field_type[annotation] = field_sql_type

            self.logger.debug(f"{annotation} {field_sql_type}{field_suffix}")
            if existing_cols and annotation in existing_cols:
                continue
            else:
                table_fields.append(f"{annotation} {field_sql_type}{field_suffix}")
        for time_field in ["created", "updated"]:
            if existing_cols and time_field in existing_cols: 
                continue
            table_fields.append(f"{time_field} TEXT NOT NULL DEFAULT(strftime('%s', 'now'))")

        cur = self.connection.cursor()

        if existing_cols:
            for f in table_fields:
                query = f'ALTER TABLE {self.table_name} ADD {f};'
                cur.execute(query)
        else:
            query = f'CREATE TABLE IF NOT EXISTS {self.table_name} (\n{",\n".join(table_fields)}\n);'
            self.logger.debug(query)
            cur.execute(query)
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

        self.field_type_map[cls] = self.field_type 
        self.primary_key_map[cls] = self.primary_key
        
    def insert(self, item: T, merge_field:str = None, id_field:str = "id"):
        """
        If the item does not exist, isnert. If it does exist, but hasn't been changed, do nothing.
        If it does exist but has been changed, update the non-null fields.
        returns True if inserted or changed, false if no db change.
        """
        item_dict = asdict(item)
        if merge_field:
            select_item = self.get(item_dict[id_field])
            if select_item and merge_field in item_dict:
                select_dict = asdict(select_item)
                if merge_field in select_dict and item_dict[merge_field] and select_dict[merge_field]:
                    if item_dict[merge_field] == select_dict[merge_field]:
                        return False
                # Else set all non null fields (Note that this will not remove should-be-nulled fields.)
                non_null_fields = [k for (k,v) in item_dict.items() if v]
                self.update(item, item_dict[id_field], non_null_fields)
                return True

        query_values = tuple(
            pickle.dumps(kv[1]) if self.field_type [kv[0]] == "BLOB" else kv[1]
            for kv in item_dict.items()
            if kv[0] in self.field_type
        )
        field_names: str =", ".join([k for k in self.field_type])
        placeholders = DbUtils.placeholder(len(self.field_type))
        query = f"INSERT OR REPLACE INTO {self.table_name} ({field_names}) VALUES({placeholders})"
        # query = f"INSERT OR REPLACE INTO {self.table_name} ({field_names}) VALUES({placeholders})"

        cur = self.connection.cursor()
        cur.execute(query, query_values)
        return True

    def get(self, item_id:str, select_fields: list[str] = None, as_tupple = False) -> T:
        field_str = "*" if not select_fields else ", ".join(select_fields)
        query = f'SELECT {field_str} FROM {self.table_name}  WHERE (id) = ?'
        self.logger.debug(query)

        cur = self.connection.cursor()
        if not as_tupple:
            cur.row_factory = DbUtils.dict_factory
        cur.execute(query, (item_id,))
        item  = cur.fetchone()

        if not item:
            return None
        elif as_tupple:
            return item
        elif select_fields:
            return item
        else:
            return dacite.from_dict(self.cls, item, config=dacite.Config(cast=[StrEnum]))

    def select(self, conditions: list[tuple], select_fields: list[str] = None, suffix = "") -> list[T]:
        if conditions:
            condition_fields, condition_vals = zip(*conditions)
            condition_query_str = " WHERE " + " AND ".join([f"{x} = ?" for x in condition_fields])
        else:
            condition_vals = None
            condition_query_str = ""
        
        has_select_fields = select_fields is not None
        select_fields = "*" if not select_fields else ", ".join(select_fields)
        query = f'SELECT {select_fields} FROM {self.table_name}{condition_query_str}{suffix}'


        self.logger.debug(query)
        cur = self.connection.cursor()
        cur.row_factory = DbUtils.dict_factory

        if condition_vals:
            cur.execute(query, (*condition_vals,))
        else:
            cur.execute(query)
        items  = cur.fetchall()

        if has_select_fields:
            return items
        elif not items:
            return []
        else:
            return [dacite.from_dict(self.cls, item, config=dacite.Config(cast=[StrEnum])) for item in items]

    def update(self, item_id:str, item: T, item_fields: list[str] = None):
        """Update list of fields. If no item field is given, replace the item."""
        if not item_fields:
            return self.insert(item)

        field_names = ", ".join(f"{item_f} = ?" for item_f in item_fields)
        query = f"UPDATE {self.table_name} SET {field_names} WHERE id = ?"
        query_values = tuple(
            pickle.dumps(kv[1]) if self.field_type [kv[0]] == "BLOB" else kv[1]
            for kv in asdict(item).items()
            if kv[0] in item_fields
        ) 
        cur = self.connection.cursor()
        cur.row_factory = DbUtils.dict_factory
        cur.execute(query, query_values + (item_id,))

    def update_fields(self, item_id:str, item_field_values: list[tuple[str, str]]):
        """Update list of fields. If no item field is given, replace the item."""

        field_names = ", ".join(f"{ifield} = ?" for ifield,_ in item_field_values)
        query_values = tuple(
            pickle.dumps(ivalue) if self.field_type [ifield] == "BLOB" else ivalue
            for ifield, ivalue in item_field_values
        ) 
        query = f"UPDATE {self.table_name} SET {field_names} WHERE id = ?"
        cur = self.connection.cursor()
        cur.row_factory = DbUtils.dict_factory
        cur.execute(query, query_values + (item_id,))

    def __contains__(self, key) -> bool:
        # key in db
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
        # with ...DB as db:
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # exiting context manager
        self.connection.commit()
        if self.connection_owner:
            self.connection.close()
        pass

if __name__ == "__main__":

    with Dataclass_DB(Post) as db:
        pass
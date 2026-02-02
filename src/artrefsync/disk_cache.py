import os

# import pickle
import functools
import logging

from typing import Callable, ParamSpec, TypeVar
from artrefsync.config import config
from artrefsync.constants import STATS, TABLE, APP
from artrefsync.db.db_utils import BlobDb
from artrefsync.stats import stats

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)
cache_dir = config[TABLE.APP][APP.CACHE_DIR]
cache_ttl = int(config[TABLE.APP][APP.CACHE_TTL])
P = ParamSpec("P")
R = TypeVar("R")


# Conig managed plain text file cache decorator
# Note*** does not work for direct module methods.
def disk_cache(func: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(func)
    def wrapper(self, *args: P.args, **kwargs: P.kwargs) -> func.__annotations__:
        cls_name = type(self).__name__
        func_name = func.__name__
        arg_str = (
            ""
            if len(args) == 0
            else ("_".join([str(x) for x in args if x is not None]))
        )
        key_name = f"{arg_str}.{func_name}.{cls_name}"

        with BlobDb(table_name_default=f"{cls_name}_{func_name}_blob") as db:
            data = db.loads_blob(key_name, cache_ttl)
            if data:
                return data
            else:
                result = func(self, *args, **kwargs)
                db.dumps_blob(key_name, result)
        return result

    return wrapper

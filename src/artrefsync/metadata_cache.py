import os
# import pickle
import jsonpickle
import hashlib
import functools
import datetime
import time
import logging

from typing import Callable, ParamSpec, Any, TypeVar
from  artrefsync.config import config
from  artrefsync.constants import *
from artrefsync.stats import stats

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)
cache_dir = config[TABLE.APP][APP.CACHE_DIR]
cache_ttl = int(config[TABLE.APP][APP.CACHE_TTL])
P = ParamSpec("P")
R = TypeVar("R")

# Conig managed plain text file cache decorator
# Note*** does not work for direct module methods.
def metadata_cache(func:Callable[P, R]) -> Callable[P,R]:
    @functools.wraps(func)
    def wrapper(self, *args: P.args, **kwargs: P.kwargs) -> func.__annotations__:
        cls_name = type(self).__name__
        func_name = func.__name__
        arg_str =  "" if len(args) == 0 else ("_".join([str(x) for x in args if x is not None]))
        f_name = f"{arg_str}.{func_name}.{cls_name}.json"

        path_name = f"{cache_dir}/{f_name}"
        path_name = path_name.replace(":", "_")
        if os.path.exists(path_name):
            file_age = time.time() - os.path.getmtime(path_name)
            logger.debug("File age %.1fs", file_age)
            if file_age < cache_ttl:
                with open(path_name, 'r', encoding="utf-8") as f:
                    logger.debug("Metatdata Cache hit. Total from cache this run: %s", stats.add(STATS.METADATA_CACHE_HIT))
                    return jsonpickle.decode(f.read())
        logger.debug("Returning results for %s and caching results to %s", func_name, f_name)
        result = func(self, *args, **kwargs)
        os.makedirs(cache_dir, exist_ok=True)

        with open(path_name, 'w', encoding="utf-8") as f:
            f.write(jsonpickle.encode(result, indent=4))
        return result
    return wrapper



if __name__ == "__main__":
    class Test:
        def __init__(self):
            pass

        @metadata_cache
        def test(self, name) -> str:
            return ("Hello " + name)
        
        def other(self):
            print(self.test.__class__)
            print(self.test.__dict__)
            print(self.test.__name__)
            print(self.test.__subclasshook__)
    t = Test()
    t.test("hi")
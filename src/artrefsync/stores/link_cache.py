import tempfile
import requests
from artrefsync.config import config
import logging

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)

def link_cache() -> "Link_Cache":
    global _link_cache
    if _link_cache is None:
        _link_cache = Link_Cache()

class Link_Cache:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._link_cache: dict[str, tempfile.NamedTemporaryFile] = {}
        self.store_count = {}
        self.store_missing = {}
        self.temp_dir = tempfile.TemporaryDirectory()
        logger.info("Link Cache Initialized with dir: %s", self.temp_dir)

    def __enter__(self):
        return self

    def set_store_missing_count(self, store, count):
        self.store_missing[store] = count

    def get_store_missing(self, store):
        return self.store_missing[store]

    def increment_store_count(self, store):
        if store not in self.store_count:
            self.store_count[store] = 0
        self.store_count[store] += 1
        return self.store_count[store]

    @staticmethod
    def download_link_to_file(link, file):
        site_response = requests.get(link, stream=True)
        site_response.raise_for_status()
        if isinstance(file, str):
            with open(file=file, mode="wb") as new_file:
                for chunk in site_response.iter_content(chunk_size=8192):
                    if chunk:
                        new_file.write(chunk)
        else:
            for chunk in site_response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)

    def get_file_from_link(self, link: str) -> str:
        if link not in self._link_cache:
            suffix = f".{link.split('.')[-1]}"
            temp = tempfile.NamedTemporaryFile(mode="wb", suffix=suffix, dir= self.temp_dir.name, delete=False)
            self.temp_dir
            self.download_link_to_file(link, temp)
            self._link_cache[link] = temp.name
        return self._link_cache[link]

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        logger.info("Cleaning up Link Cache. Removing temp dir: %s.", self.temp_dir)
        self.temp_dir.cleanup()
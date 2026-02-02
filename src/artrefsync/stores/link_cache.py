# CACHE links
# module enforced static members.
import os
import tempfile
import time
import requests
from artrefsync.config import config
import logging


logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


class Link_Cache:
    def __init__(self):
        self._link_cache: dict[str, tempfile.NamedTemporaryFile] = {}
        self.store_count = {}
        self.store_missing = {}

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
        # print(f"{link} {file.name}")
        time.sleep(0.1)

    def get_file_from_link(self, link: str) -> str:
        if link not in self._link_cache:
            # print("Downloading {link} to cache")
            suffix = f".{link.split('.')[-1]}"
            temp = tempfile.NamedTemporaryFile(mode="wb", suffix=suffix, delete=False)
            self.download_link_to_file(link, temp)
            self._link_cache[link] = temp.name
        return self._link_cache[link]

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


    def close(self):
        for file in self._link_cache.values():
            os.remove(file)

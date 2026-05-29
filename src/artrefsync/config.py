# Config Related setup
import functools
import logging
import logging.handlers
import os
import sys

from diskcache import Cache
from simple_toml_configurator import Configuration

from artrefsync.constants import (
    APP,
    BOARD,
    DANBOORU,
    DB,
    E621,
    EAGLE,
    LOCAL,
    R34,
    STORE,
    TABLE,
)
from artrefsync.utils.utils import singleton

__all__ = ["config"]


@singleton
class Config:
    def __init__(self, config_path="config", config_file_name="config"):
        self.kwargs = {
            "config_path": config_path,
            "defaults": self.default_config,
            "config_file_name": config_file_name,
        }
        self._subscribed_reload = []
        self._reload_config()
        self.__caches = {}

    def _reload_config(self):
        self.settings = Configuration(**self.kwargs)
        self.path = self.settings._full_config_path
        self.log_level = self.settings.get_settings()["app_log_level"]

        self.log_file = "log/art_sink.log"
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        log_file_handler = logging.handlers.TimedRotatingFileHandler(
            self.log_file, encoding="utf-8"
        )
        log_file_handler.suffix = "%Y-%m-%d.log"
        logging.basicConfig(
            level=self.log_level,
            format="%(asctime)s %(name)s %(funcName)s (%(levelname)s): %(message)s",
            datefmt="%I:%M:%S",
            handlers=[
                logging.StreamHandler(sys.stdout),
                log_file_handler,
            ],
        )
    
    repl_text = "₊✩‧₊˚౨ৎ˚₊✩‧₊₊✩‧₊˚౨ৎ˚₊✩‧₊₊✩‧₊˚౨ৎ˚₊✩‧₊₊✩‧₊˚౨ৎ˚₊✩‧₊✩‧₊˚౨ৎ˚₊✩‧₊₊✩‧₊˚౨ৎ˚₊✩‧₊₊✩‧₊˚౨ৎ˚₊✩‧₊₊✩‧₊˚౨ৎ˚₊✩‧₊₊"
    @functools.lru_cache
    def censor_text(self, text):
        if config[TABLE.APP][APP.BLUR_UNSAFE_ENABLED]:
            repl_split = "_".join(
                [
                    split[0]
                    + Config.repl_text[len(split) : 2 * len(split) - 2]
                    + split[-1]
                    for split in text.split("_")
                ]
            )
            return text[0] + repl_split[1:-1] + text[-1]


    def cache(self, subdir : str = "") -> Cache:
        key = f"{config[TABLE.APP][APP.CACHE_DIR]}/{subdir}"
        if key not in self.__caches:
            self.__caches[key] = Cache(key)
        return self.__caches[key]

    def subscribe_reload(self, func: callable):
        self._subscribed_reload.append(func)

    # Reloads config alongside all subscribed in _subscribed_reload
    def reload_config(self, reset=False):
        if reset:
            self._reload_config()
        else:
            config.settings.update()

        for reload in self._subscribed_reload:
            reload()

    def __getitem__(self, field: TABLE | STORE | BOARD) -> dict:
        return self.settings.config[field]

    def get(
        self, table: TABLE, field: TABLE | STORE | BOARD, default
    ) -> dict[R34 | E621 | EAGLE | LOCAL,]:

        try:
            return self.settings.config[table][field]
        except KeyError:
            return default

    def cache_ttl(self):
        return int(self.get(TABLE.APP, APP.CACHE_TTL, 300))

    default_config = {
        TABLE.APP: {
            APP.LIMIT: 5000,
            APP.LOG_LEVEL: "INFO",
            APP.ID_LENGTH: 8,
            APP.CACHE_DIR: ".metadata_cache",
            APP.CACHE_TTL: 300,
            APP.DB_DIR: ".db",
            APP.DB_FILE_NAME: DB.TAGAPP_DB,
            APP.DB_BLOB_NAME: DB.BLOB_DB,
            APP.THUMBNAIL_WIDTH: 1280,
            APP.THUMBNAIL_HEIGHT: 720,
            APP.ONLY_RECENT_ENABLED: True,
            APP.MAX_DOWNLOAD_THREADS: 8,
            APP.BLUR_UNSAFE_ENABLED: False,
        },
        TABLE.R34: {
            R34.ENABLED: False,
            R34.ARTISTS: [],
            R34.BLACK_LIST: [],
            R34.API_KEY: "",
        },
        TABLE.E621: {
            E621.ENABLED: False,
            E621.ARTISTS: [],
            E621.BLACK_LIST: [],
            E621.API_KEY: "",
            E621.USERNAME: "",
        },
        TABLE.DANBOORU: {
            DANBOORU.ENABLED: False,
            DANBOORU.ARTISTS: [],
            DANBOORU.BLACK_LIST: [],
            DANBOORU.API_KEY: "",
            DANBOORU.USERNAME: "",
        },
        TABLE.EAGLE: {
            EAGLE.ENABLED: False,
            EAGLE.ENDPOINT: "http://localhost:41595/api",
            EAGLE.LIBRARY: "",
            EAGLE.ARTIST_FOLDER: "",
        },
        TABLE.LOCAL: {
            LOCAL.ENABLED: True,
            LOCAL.ARTIST_DIR: "media",
        },
    }


config = Config()
# config.cache(""): Cache = Cache(config[TABLE.APP][APP.CACHE_DIR])



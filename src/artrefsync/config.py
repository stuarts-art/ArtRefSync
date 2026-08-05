# Config Related setup
import functools
import logging
import logging.handlers
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

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
from artrefsync.utils.utils import resource_path

__all__ = ["Config", "get_config", "set_config"]


class Config:
    def __init__(self, config_path="config", config_file_name="config"):
        self.config_path = config_path
        self.config_file_name = config_file_name
        self._subscribed_reload = []
        self.__caches = {}
        self._reload_config(self.config_path, self.config_file_name)

    def _reload_config(self, config_path=None, config_file_name=None):
        kwargs = {
            "config_path": config_path if config_path else self.config_path,
            "defaults": self.default_config,
            "config_file_name": config_file_name
            if config_file_name
            else self.config_file_name,
        }
        self.settings = Configuration(**kwargs)
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
        if self[TABLE.APP][APP.BLUR_UNSAFE_ENABLED]:
            repl_split = "_".join(
                [
                    split[0]
                    + Config.repl_text[len(split) : 2 * len(split) - 2]
                    + split[-1]
                    for split in text.split("_")
                ]
            )
            return text[0] + repl_split[1:-1] + text[-1]

    def cache(self, subdir: str = "") -> Cache:
        key = resource_path(f"{self[TABLE.APP][APP.CACHE_DIR]}/{subdir}")
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
            backup = Path(self.config_path) / "backups"
            os.makedirs(backup, exist_ok=True)
            backup_file = (
                backup
                / f"{datetime.today().strftime('%Y.%m.%d_%H.%M.%S')}.{self.config_file_name}.toml"
            )
            shutil.copy(self.settings._full_config_path, backup_file)

            self.settings.update()

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

    default_config = {  # noqa: RUF012
        TABLE.APP: {
            APP.THEME: "bootstrap-dark",
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


_config: Config = None


def get_config():
    global _config
    if not _config:
        _config = Config()
    return _config


def set_config(config: Config):
    global _config
    _config = config

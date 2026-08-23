__all__ = ["Config", "get_config", "set_config"]
# Config Related setup
import logging
import logging.handlers
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

from diskcache import Cache
from simple_toml_configurator import Configuration

from artrefsync.constants import (
    APP,
    BOARD,
    E621,
    EAGLE,
    LOCAL,
    R34,
    STORE,
    TABLE,
)
from artrefsync.default_config import default_config
from artrefsync.utils.utils import censor_text

logger = logging.getLogger(__name__)


class Config:
    def __init__(
        self, config_path="config", config_file_name="config", internal_override=""
    ):
        self.config_path = config_path
        self.config_file_name = config_file_name
        self._subscribed_reload = []
        self.__caches = {}
        self._reload_config(self.config_path, self.config_file_name)
        self._internal_override = internal_override

    def _reload_config(self, config_path=None, config_file_name=None):
        kwargs = {
            "config_path": config_path if config_path else self.config_path,
            "defaults": default_config,
            "config_file_name": (
                config_file_name if config_file_name else self.config_file_name
            ),
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
        logger.info(
            "Config initialized with config_path = %s, config_file_name = %s",
            config_path,
            config_file_name,
        )

    def resource_path(self, relative_path):
        if os.path.isabs(relative_path):
            return Path(relative_path)
        try:
            if self._internal_override:
                base_path = self._internal_override
            else:
                base_path = sys._MEIPASS
        except Exception:  # noqa: BLE001
            base_path = os.path.abspath("./_internal")
            os.makedirs(base_path, 0o771, exist_ok=True)

        return Path(os.path.join(base_path, relative_path)).resolve()

    def cache(self, subdir: str = "") -> Cache:
        key = self.resource_path(f"{self[TABLE.APP][APP.CACHE_DIR]}/{subdir}")
        if key not in self.__caches:
            self.__caches[key] = Cache(key)
        return self.__caches[key]

    def subscribe_reload(self, func: callable):
        self._subscribed_reload.append(func)

    def reload_config(self, reset=False):
        if reset:
            self._reload_config()
        else:
            backup = Path(self.config_path) / "backups"
            os.makedirs(backup, exist_ok=True)
            backup_file = (
                backup
                / f"{datetime.now(UTC).strftime('%Y.%m.%d_%H.%M.%S')}.{self.config_file_name}.toml"
            )
            shutil.copy(self.settings._full_config_path, backup_file)

            self.settings.update()

        for reload in self._subscribed_reload:
            reload()

    def __getitem__(self, field: TABLE | STORE | BOARD) -> dict:
        if (
            type(field) is str
            or isinstance(field, TABLE)
            or isinstance(field, BOARD)
            or isinstance(field, STORE)
        ):
            return self.settings.config[field]
        else:
            class_name = field.__class__.__name__.lower()
            value = field.value
            return self.settings.config[class_name][value]

    def get(
        self, table: TABLE, field: TABLE | STORE | BOARD, default
    ) -> dict[R34 | E621 | EAGLE | LOCAL,]:

        try:
            return self.settings.config[table][field]
        except KeyError:
            return default

    def cache_ttl(self):
        return int(self.get(TABLE.APP, APP.CACHE_TTL, 300))


_config: Config = None


def set_config(config: Config):
    global _config
    _config = config


def get_config():
    if _config is None:
        set_config(Config())
    return _config

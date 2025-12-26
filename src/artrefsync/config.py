# Config Related setup
from simple_toml_configurator import Configuration
from artrefsync.constants import R34, E621, TABLE, LOCAL, EAGLE, APP, STORE, BOARD
import logging




__all__ = ["config"]
class __Config:

    def __init__(self, config_path = "config", config_file_name = "config"):
        self.kwargs = {"config_path": config_path, "defaults": self.default_config, "config_file_name": config_file_name}
        self._reload_config()


    def _reload_config(self):
        self.settings = Configuration(**self.kwargs)
        self.path = self.settings._full_config_path
        self.log_level = self.settings.get_settings()["app_log_level"]
        self._subscribed_reload = []

        logging.basicConfig(format="%(asctime)s %(funcName)s(%(levelname)s): %(message)s", datefmt="%I:%M:%S")
        fh = logging.FileHandler('app.log')
        fh.setLevel(self.log_level)
        ch = logging.StreamHandler()
        ch.setLevel(self.log_level)

        logging.basicConfig(handlers=[fh, ch])
   
    def subscribe_reload(self, func: callable):
        self._subscribed_reload.append(func)


    # Reloads config alongside all subscribed in _subscribed_reload
    def reload_config(self, reset = False):
        if reset:
            self._reload_config()
        else:
            config.settings.update()
        
        for reload in self._subscribed_reload:
            reload()

        
    
    def __getitem__(self, field:TABLE|STORE|BOARD) -> dict[R34|E621|EAGLE|LOCAL,]:
        return self.settings.config[field]
    
    default_config = {
        TABLE.APP: {
            APP.LIMIT: 10,
            APP.LOG_LEVEL: "INFO",
            APP.ID_LENGTH: 8,
            APP.CACHE_DIR: "metadata_cache",
            APP.CACHE_TTL: 300
        },
        TABLE.R34: {
            R34.ENABLED: False,
            R34.ARTISTS: [],
            R34.BLACK_LIST: [],
            R34.API_KEY: ""
        },
        TABLE.E621: {
            E621.ENABLED: False,
            E621.ARTISTS: [],
            E621.BLACK_LIST: [],
            E621.API_KEY: "",
            E621.USERNAME: ""
        },
        TABLE.EAGLE: {
            EAGLE.ENABLED: False,
            EAGLE.ENDPOINT: "http://localhost:41595/api",
            EAGLE.LIBRARY: "",
            EAGLE.ARTIST_FOLDER: ""
        },
        TABLE.LOCAL: {
            LOCAL.ENABLED: False,
            LOCAL.ARTIST_FOLDER: ""
        },
    }

config = __Config()
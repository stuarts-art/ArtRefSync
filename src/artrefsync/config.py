# Config Related setup
from simple_toml_configurator import Configuration
from artrefsync.constants import R34, E621, TABLE, LOCAL, EAGLE, APP, STORE, BOARD

def main():
    config = Config()


class Config:
    def __init__(self, config_path = "config", config_name = "config"):
       self.settings = Configuration(config_path, self.default_config, config_name)
    
    def __getitem__(self, field:TABLE|STORE|BOARD) -> dict[R34|E621|EAGLE|LOCAL,]:
        return self.settings.config[field]
    
    default_config = {
        TABLE.APP: {
            APP.LIMIT: 10
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
        }
    }

if __name__ == "__main__":
    main()
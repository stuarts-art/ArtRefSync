# Config Related setup
from simple_toml_configurator import Configuration
from artrefsync.constants import R34, E621, TABLE, LOCAL, EAGLE

def main():
    config = Config()


class Config:
    def __init__(self, config_path = "config", config_name = "config"):
       self.settings = Configuration(config_path, self.default_config, config_name)
    
    def update(self):
        self.settings.update()

    
    def getR34(self, field: R34 = None):
        if field:
            return self.settings.config[TABLE.R34][field]
        else:
            return self.settings.config[TABLE.R34]
    def getE621(self, field: E621):
        if field:
            return self.settings.config[TABLE.E621][field]
        else:
            return self.settings.config[TABLE.E621]
    def getEAGLE(self, field: EAGLE):
        if field:
            return self.settings.config[TABLE.EAGLE][field]
        else:
            return self.settings.config[TABLE.EAGLE]
    def getLOCAL(self, field: LOCAL):
        if field:
            return self.settings.config[TABLE.LOCAL][field]
        else:
            return self.settings.config[TABLE.LOCAL]

    def setR34(self, field: R34, val):
        self.settings.config[TABLE.R34][field] = val
    def setE621(self, field: E621, val):
        self.settings.config[TABLE.E621][field] = val
    def setEagle(self, field: EAGLE, val):
        self.settings.config[TABLE.EAGLE][field] = val
    def setLOCAL(self, field: LOCAL, val):
        self.settings.config[TABLE.LOCAL][field] = val

    default_config = {
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
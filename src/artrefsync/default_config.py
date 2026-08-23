from artrefsync.constants import APP, DANBOORU, DB, E621, EAGLE, HOTKEY, LOCAL, R34, TABLE


from enum import StrEnum
from typing import Any


default_config: dict[StrEnum, dict[StrEnum, Any]] = {
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
        R34.BLACK_LIST: ["ai_generated"],
        R34.API_KEY: "",
    },
    TABLE.E621: {
        E621.ENABLED: False,
        E621.ARTISTS: [],
        E621.BLACK_LIST: ["ai_generated"],
        E621.API_KEY: "",
        E621.USERNAME: "",
    },
    TABLE.DANBOORU: {
        DANBOORU.ENABLED: False,
        DANBOORU.ARTISTS: [],
        DANBOORU.BLACK_LIST: ["ai_generated"],
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
    TABLE.HOTKEY: {
        HOTKEY.UP_LIST: ["w", "k", "Up"],
        HOTKEY.LEFT_LIST: ["a", "h", "Left"],
        HOTKEY.DOWN_LIST: ["s", "j", "Down"],
        HOTKEY.RIGHT_LIST: ["d", "l", "Right"],
        HOTKEY.ZOOM_OUT_LIST: ["q", "u", "minus"],
        HOTKEY.ZOOM_IN_LIST: ["e", "o", "equal"],
        HOTKEY.ZOOMED_PREV_LIST: ["z", "m", "underscore"],
        HOTKEY.ZOOMED_NEXT_LIST: ["c", "period", "plus"],
        
    }
}
from enum import StrEnum
from typing import Any

from artrefsync.constants import (
    APP,
    DANBOORU,
    DB,
    E621,
    EAGLE,
    HOTKEY,
    LOCAL,
    R34,
    TABLE,
)

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
        APP.DOWNLOAD_SIZE_DOWN: 1440,
        APP.FORMAT_LIST: ["jpg", "png", "webp", "gif", "mp4", "webm"],
        APP.THUMBNAIL_WIDTH: 1280,
        APP.THUMBNAIL_HEIGHT: 720,
        APP.ONLY_RECENT_ENABLED: True,
        APP.MAX_DOWNLOAD_THREADS: 8,
        APP.BLUR_UNSAFE_ENABLED: False,
        APP.PREVIEW_ENABLED: True
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
        HOTKEY.UP_LIST: ["w", "k", "Up", "W", "K"],
        HOTKEY.LEFT_LIST: ["a", "h", "Left", "A", "H"],
        HOTKEY.DOWN_LIST: ["s", "j", "Down", "S", "J"],
        HOTKEY.RIGHT_LIST: ["d", "l", "Right", "D", "L"],
        HOTKEY.ZOOM_OUT_LIST: ["q", "u", "minus"],
        HOTKEY.ZOOM_IN_LIST: ["e", "o", "equal"],
        HOTKEY.ZOOMED_PREV_LIST: ["z", "m", "underscore"],
        HOTKEY.ZOOMED_PAUSE_LIST: ["x", "comma"],
        HOTKEY.ZOOMED_NEXT_LIST: ["c", "period", "plus"],
        HOTKEY.OPEN_LIST: ["space", "semicolon"],
        HOTKEY.SEARCH_LIST: ["Return", "i"],
        HOTKEY.DELETE_LIST: ["BackSpace", "slash"],
        HOTKEY.SWAP_LIST: ["Tab", "n"]
    },
}

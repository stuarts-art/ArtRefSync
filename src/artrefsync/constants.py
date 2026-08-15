from enum import StrEnum, auto

__all__ = [
    "APP",
    "BOARD",
    "DANBOORU",
    "E621",
    "EAGLE",
    "LOCAL",
    "R34",
    "STATS",
    "STORE",
    "TABLE",
    "TAGS",
    "get_table_mapping",
]


class NAMES(StrEnum):
    VIEWER_TAB = auto()


class TK(StrEnum):
    KEY_PRESS = "2"
    MOUSE_PRESS = "5"

class ICON(StrEnum):
    FOLDER_OPEN = "🗁"
    FOLDER_CLOSED = "🗀"
    TAG = "🏷"
    INFO = "ⓘ"
    SETTINGS = '⚙'
    ARTISTS = "🎨"

class BINDING(StrEnum):
    GALLERY_WIDGET = auto()
    VIEWER_WIDGET = auto()
    # Mapped vars
    ARTIST_SET = auto()
    BOARD_SET = auto()
    BOARD_ARTIST_MAP = auto()
    SORT_BY = auto()
    SORT_DIR = auto()
    SYNC_LOCK = auto()

    ON_LOAD_LEFT_SET = auto()
    ON_LOAD_MID_SET = auto()
    ON_LOAD_RIGHT_SET = auto()
    ON_LOAD_LEFT_INCR = auto()
    ON_LOAD_RIGHT_INCR = auto()
    ON_LOADING_DONE = auto()
    ON_POST_SELECT = auto()
    ON_POST_FOCUS_CHANGE = auto()
    ON_PREV_GALLERY_IMAGE = auto()
    ON_NEXT_GALLERY_IMAGE = auto()
    ON_IMAGE_VISIBILITY = auto()
    ON_IMAGE_DOUBLE_CLICK = auto()
    ON_ARTIST_SELECT = auto()
    ON_ARTIST_SYNC = auto()
    ON_ARTIST_SYNC_DONE = auto()
    ON_ARTIST_CLEAR = auto()
    ON_TAG_SELECT = auto()
    ON_FILTER_UPDATE = auto()
    ON_SORT_BY_UPDATE = auto()
    ON_SET_TOP_RIGHT_TEXT = auto()
    ON_ZOOM_DELTA = auto()

    ON_TEXT_ESCAPE = auto()
    ON_TEXT_Z = auto()
    ON_TEXT_X = auto()
    ON_TEXT_C = auto()
    ON_TEXT_TAB = auto()
    ON_TEXT_SHIFT_TAB = auto()


class DB(StrEnum):
    TAGAPP_DB = "tagapp.db"
    BLOB_DB = "blob.db"


class DB_TABLE(StrEnum):
    TAG_POSTS = auto()
    POSTS = auto()
    POST_FILE = auto()
    POST_TAGS = auto()
    POST_IMAGES = auto()
    METADATA = auto()


def get_table_mapping():
    return {
        TABLE.APP: APP,
        TABLE.R34: R34,
        TABLE.E621: E621,
        TABLE.DANBOORU: DANBOORU,
        TABLE.EAGLE: EAGLE,
        TABLE.LOCAL: LOCAL,
    }


class TABLE(StrEnum):
    APP = auto()
    R34 = auto()
    E621 = auto()
    DANBOORU = auto()
    EAGLE = auto()
    LOCAL = auto()


class APP(StrEnum):
    THEME = auto()
    LIMIT = auto()
    LOG_LEVEL = auto()
    ID_LENGTH = auto()
    CACHE_DIR = auto()
    CACHE_TTL = auto()
    DB_DIR = auto()
    DB_FILE_NAME = auto()
    DB_BLOB_NAME = auto()
    THUMBNAIL_WIDTH = auto()
    THUMBNAIL_HEIGHT = auto()
    ONLY_RECENT_ENABLED = auto()
    MAX_DOWNLOAD_THREADS = auto()
    BLUR_UNSAFE_ENABLED = auto()


class BOARD(StrEnum):
    R34 = auto()
    E621 = auto()
    DANBOORU = auto()
    OTHER = auto()


class STORE(StrEnum):
    EAGLE = auto()
    LOCAL = auto()


class DANBOORU(StrEnum):
    ENABLED = auto()
    ARTISTS = auto()
    BLACK_LIST = auto()
    API_KEY = auto()
    USERNAME = auto()


class R34(StrEnum):
    ENABLED = auto()
    ARTISTS = auto()
    BLACK_LIST = auto()
    API_KEY = auto()


class E621(StrEnum):
    ENABLED = auto()
    ARTISTS = auto()
    BLACK_LIST = auto()
    API_KEY = auto()
    USERNAME = auto()


class EAGLE(StrEnum):
    ENABLED = auto()
    ENDPOINT = auto()
    LIBRARY = auto()
    ARTIST_FOLDER = auto()


class LOCAL(StrEnum):
    ENABLED = auto()
    ARTIST_DIR = auto()


class TAGS(StrEnum):
    ARTIST = auto()
    CHARACTER = auto()
    SPECIES = auto()
    RATING = auto()
    META = auto()
    UNDEFINED = auto()


class STATS(StrEnum):
    TAG_SET = auto()
    ARTIST_SET = auto()
    CHARACTER_SET = auto()
    SPECIES_SET = auto()
    RATING_SET = auto()
    META_SET = auto()
    COPYRIGHT_SET = auto()
    POST_COUNT = auto()
    SKIP_COUNT = auto()
    FAILED_COUNT = auto()
    METADATA_CACHE_HIT = auto()


class TTKColor(StrEnum):
    PRIMARY = auto()
    SECONDARY = auto()
    SUCCESS = auto()
    INFO = auto()
    WARNING = auto()
    DANGER = auto()
    LIGHT = auto()
    DARK = auto()
    BG = auto()
    FG = auto()
    SELECTBG = auto()
    SELECTFG = auto()
    BORDER = auto()
    INPUTFG = auto()
    INPUTBG = auto()
    ACTIVE = auto()

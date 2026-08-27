from enum import Enum, StrEnum, auto

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


class EVENT:
    # Tk Event Constants
    class TYPE(StrEnum):
        KEY = "2"
        BUTTON = "5"

    class NUM(Enum):
        LEFT = 1
        MIDDLE = 2
        RIGHT = 3


class ICON(StrEnum):
    FOLDER_OPEN = "🗁"
    FOLDER_CLOSED = "🗀"
    TAG = "🏷"
    INFO = "ⓘ"
    SETTINGS = "⚙"
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

    # Run: Triggers event
    RUN_FOCUS_GALLERY = auto()
    RUN_TAG_REMOVE_LAST = auto()
    RUN_SYNC = auto()
    RUN_STORE_SYNC = auto()

    # On: Triggered by event
    ON_ARTIST_CLEAR = auto()
    ON_ARTIST_SELECT = auto()
    ON_ARTIST_UPDATE = auto()
    ON_DB_UPDATE = auto()
    ON_FILTER_UPDATE = auto()
    ON_IMAGE_DOUBLE_CLICK = auto()
    ON_IMAGE_VISIBILITY = auto()
    ON_LOAD_LEFT_INCR = auto()
    ON_LOAD_LEFT_SET = auto()
    ON_LOAD_MID_SET = auto()
    ON_LOAD_RIGHT_INCR = auto()
    ON_LOAD_RIGHT_SET = auto()
    ON_LOADING_DONE = auto()
    ON_NEXT_GALLERY_IMAGE = auto()
    ON_POST_FOCUS_CHANGE = auto()
    ON_POST_SELECT = auto()
    ON_PREV_GALLERY_IMAGE = auto()
    ON_SET_TOP_RIGHT_TEXT = auto()
    ON_SORT_BY_UPDATE = auto()
    ON_TAG_SELECT = auto()
    ON_TOGGLE_UI = auto()
    ON_CLOSE_VIEWER = auto()
    ON_ZOOM_DELTA = auto()
    ON_GALLERY_SHIFT_TAB = auto()
    ON_ICON_TAG = auto()
    ON_ICON_ARTIST = auto()
    ON_ICON_INFO = auto()
    ON_ICON_CONFIG = auto()

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
        TABLE.HOTKEY: HOTKEY,
    }


class TABLE(StrEnum):
    APP = auto()
    R34 = auto()
    E621 = auto()
    DANBOORU = auto()
    EAGLE = auto()
    LOCAL = auto()
    HOTKEY = auto()


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


class HOTKEY(StrEnum):
    LEFT_LIST = auto()
    RIGHT_LIST = auto()
    UP_LIST = auto()
    DOWN_LIST = auto()
    ZOOM_IN_LIST = auto()
    ZOOM_OUT_LIST = auto()
    ZOOMED_NEXT_LIST = auto()
    ZOOMED_PREV_LIST = auto()


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

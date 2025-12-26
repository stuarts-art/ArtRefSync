from enum import StrEnum, auto

__all__ = [
    'get_table_mapping', 'TABLE', 'APP', 'BOARD', 'STORE', 
    'R34', 'E621', 'EAGLE', 'LOCAL', 'TAGS', 'STATS'
]


def get_table_mapping():
    return {
        TABLE.APP: APP,
        TABLE.R34: R34,
        TABLE.E621: E621,
        TABLE.EAGLE: EAGLE,
        TABLE.LOCAL: LOCAL
    }

class TABLE(StrEnum):
    APP = auto()
    R34 = auto()
    E621 = auto()
    EAGLE = auto()
    LOCAL = auto()

class APP(StrEnum):
    LIMIT = auto()
    LOG_LEVEL = auto()
    ID_LENGTH = auto()
    CACHE_DIR = auto()
    CACHE_TTL = auto()

class BOARD(StrEnum):
    R34 = auto()
    E621 = auto()
    OTHER = auto()
    


class STORE(StrEnum):
    EAGLE = auto()
    LOCAL = auto()

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
    # LIBRARY = auto()
    ARTIST_FOLDER = auto()

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
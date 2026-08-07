import pytest

from artrefsync.config import config
from artrefsync.constants import EAGLE, TABLE
from artrefsync.stores.eagle_db import EagleDb

with EagleDb() as edb:
    pass


def test_get_all():

    with EagleDb(refresh=True) as edb:
        folders = edb.folder.get_all()
        assert folders


def test_get_artist_folder():
    artists_folder_name = config[TABLE.EAGLE][EAGLE.ARTIST_FOLDER]
    with EagleDb() as eagle_db:
        assert artists_folder_name in eagle_db
        folder = eagle_db[artists_folder_name]
        assert folder
        
        sub_folders = eagle_db.get_sub_folders(artists_folder_name)
        assert sub_folders

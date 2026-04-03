import logging
import os
import tempfile
from asyncio import Event
from pathlib import Path

from artrefsync.api.eagle_client import EagleClient
from artrefsync.api.eagle_model import EagleFolder, EagleItem
from artrefsync.boards.board_handler import PostFile
from artrefsync.config import config
from artrefsync.constants import BOARD, DANBOORU, E621, EAGLE, R34, STORE, TABLE
from artrefsync.stores.link_cache import LinkCache
from artrefsync.stores.storage import ImageStoreHandler, Post
from artrefsync.utils import str_dict

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)

def main():
    pass


class EagleHandler(ImageStoreHandler):
    """
    Helper class for interacting with Eagle using https://api.eagle.cool/
    """

    def __init__(self):
        logger.info("Initializing Eagle Handler")
        self.client = EagleClient()
        self.reload_config()
        config.subscribe_reload(self.reload_config)

    def reload_config(self):
        self.library = config[TABLE.EAGLE][EAGLE.LIBRARY]
        self.artists_folder_name = config[TABLE.EAGLE][EAGLE.ARTIST_FOLDER]
        self._artist_folder: EagleFolder.ListFolder= None
        self.board_id_map = str_dict()
        self.board_artist_id_map = str_dict(dict)
        self.id_artist_map = {}
        self.library_path_dict = {}
        self.switch_libary(self.library)
        self.get_artists_folder()
        logger.debug("%s \n%s", "Board Artist dict:", self.board_artist_id_map)

    def get_store(self):
        return STORE.EAGLE

    def post_add_from_path(self, post: Post, path: str) -> str:
        artist_folder = self.get_board_artist_id(post.board, post.artist_name)
        return self.client.item.post_add_from_path(
            path=path,
            name=post.name,
            website=post.website,
            tags=post.tags,
            folder_id=artist_folder,
        )

    def get_list_items(
        self, limit=10000, folders=None, post_limit=None
    ) -> list[EagleItem.Item]:
        data = []
        for offset in range(100):
            items = self.client.item.list_items(
                limit=limit, offset=offset, folders=folders
            )
            data.extend(items)
            if limit and len(items) < limit:
                break
            if post_limit and len(data) > post_limit:
                break
        return data

    def eagle_item_to_postfile(
        self, item: EagleItem.Item, artist_name=None, artist_board=BOARD.OTHER
    ) -> Post | None:
        pid = Post.parse_id(item.name)
        lib = self.library_path_dict[self.library]
        board_path = Path(os.path.join(lib, "images", f"{item.id}.info"))
        thumbnail = ""
        f"{self.library_path_dict[self.library]}/images/{item.id}.info/{item.name}.{item.ext}"
        for path in board_path.iterdir():
            strpath = str(path)
            if "metadata.json" in strpath:
                continue
            if "thumbnail" in strpath:
                thumbnail = strpath
            else:
                pass

        height = item.height
        width = item.height
        ratio = item.height / item.width if item.height and item.width else None

        postfile = PostFile(
            id=pid,
            ext_id=item.id,  # External ID
            store=self.get_store(),
            board=None,
            preview=thumbnail,
            thumbnail=thumbnail,
            height=height,
            width=width,
            ratio=ratio,
            file=f"{self.library_path_dict[self.library]}/images/{item.id}.info/{item.name}.{item.ext}",
        )
        return postfile

    def create_board_and_artist_folders(self, board: BOARD, artists: list[str]):
        self.get_artists_folder()
        for artist in artists:
            self.get_board_artist_id(board, artist)

    def get_board_artist_id(self, board: BOARD, artist: str) -> EagleFolder.ListFolder:
        if board not in self.board_id_map:
            board_folder = self.client.folder.create(board, self.get_artists_folder().id)
            self.board_id_map[board] = board_folder.id
        if artist not in self.board_artist_id_map[board]:
            artist_folder = self.client.folder.create(artist, self.board_id_map[board])
            self.board_artist_id_map[board][artist] = artist_folder.id
            self.id_artist_map[artist_folder.id] = artist
        return self.board_artist_id_map[board][artist]

    # Assuming that we will always call get_posts before save_posts
    def get_posts(self, board: BOARD, artist: str) -> dict[str, PostFile]:
        data = self.get_list_items(folders=self.board_artist_id_map[board][artist])
        post_files = {}
        for item in data:
            post_file = self.eagle_item_to_postfile(item)
            if post_file:
                post_files[post_file.id] = post_file
        logger.debug(f"Eagle Items for {board}, {artist} - {len(post_files)}")
        return post_files

    def save_post(
        self, post: Post, link_cache: LinkCache, event: Event = None
    ) -> str | None:
        if event and event.is_set():
            return
        if link_cache:
            # loading(link_cache.increment_store_count(self.get_store())/link_cache.get_store_missing(self.get_store()))
            eagle_id = self.post_add_from_path(
                post, link_cache.get_file_from_link(post.url)
            )
        else:
            suffix = f".{post.url.split('.')[-1]}"
            with tempfile.NamedTemporaryFile(mode="wb", suffix=suffix) as f:
                LinkCache.download_link_to_file(post.url, tempfile)
                eagle_id = self.post_add_from_path(post, f.name)
        eagle_item = self.client.item.info(eagle_id)
        return self.eagle_item_to_postfile(eagle_item, post.artist_name, post.board)

    def update_post(self, post: Post):
        self.client.item.update(post.ext_id, post.tags, url=post.url)

    def get_artists_folder(self, refresh = False) -> EagleFolder.ListFolder:
        if self._artist_folder is not None:
            if not refresh:
                return self._artist_folder
        for folder in self.client.folder.list():
            if folder.name == self.artists_folder_name:
                self._artist_folder = folder
                break
        if not self._artist_folder:
            logger.info("Creating Artists (Main Parent) Folder: %s", self.artists_folder_name)
            self._artist_folder = self.client.folder.create(self.artists_folder_name)

        logger.info("Artist Folder ID: %s", self._artist_folder.id)
        for board_folder in self._artist_folder.children:
            board_name = board_folder.name
            self.board_id_map[board_name] = board_folder.id
            self.board_artist_id_map[board_name] = {}
            for artist in board_folder.children:
                artist_name = artist.name
                self.board_artist_id_map[board_name][artist_name] = artist.id
                self.id_artist_map[artist.id] = artist_name
            logger.info("Board %s, Artist Count: %d", board_name, len(self.board_artist_id_map[board_name]))

    def switch_libary(self, library_string):
        history = self.client.library.history()
        for path in history:
            library_str = path.split("/")[-1]
            library_str = library_str.removesuffix(".library")
            self.library_path_dict[library_str] = path
        try:
            if library_string in self.library_path_dict:
                response = self.client.library.switch(
                    self.library_path_dict[library_string]
                )
                logger.debug(
                    "Switch Library to %s response: %s.", library_string, response
                )
            else:
                logger.warning('Failed to find library "%s" in History', library_string)
        except Exception as e:
            logger.error(e)

    def get_thumbnail(self, post):
        return self.client.item.thumbnail(post.ext_id)

    def update_thumbnails(self, board: BOARD, artist:str):
        pass

if __name__ == "__main__":
    main()
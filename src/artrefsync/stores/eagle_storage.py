import logging
import os
import tempfile
from asyncio import Event
from pathlib import Path

from artrefsync.api.eagle_client import EagleClient
from artrefsync.api.eagle_model import EagleFolder, EagleItem
from artrefsync.boards.board_handler import PostFile
from artrefsync.config import config
from artrefsync.constants import BOARD, EAGLE, STORE, TABLE
from artrefsync.stores.link_cache import Link_Cache
from artrefsync.stores.storage import ImageStoreHandler, Post
from artrefsync.utils.str_dict import str_dict

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)

def main():
    handler = EagleHandler()


class EagleHandler(ImageStoreHandler):
    """
    Helper class for interacting with Eagle using https://api.eagle.cool/
    """

    def __init__(self):
        logger.info("Initializing Eagle Handler")
        self.reload_config()
        config.subscribe_reload(self.reload_config)

    def reload_config(self):
        self.library = config.get(TABLE.EAGLE,EAGLE.LIBRARY)
        self.artists_folder_name = config.get(TABLE.EAGLE, EAGLE.ARTIST_FOLDER, "artists").strip()

        self.client = EagleClient()
        self._artist_folder: EagleFolder.ListFolder= None
        self.board_id_map = str_dict()
        self.board_artist_id_map = str_dict(dict)
        self.id_artist_map = {}

        self.library_path_dict = {}
        history = self.client.library.history()
        for path in history:
            library_str = path.split("/")[-1]
            library_str = library_str.removesuffix(".library")
            self.library_path_dict[library_str] = path

        self.switch_libary(self.library)
        self.get_artists_folder()
        logger.debug("%s \n%s", "Board Artist dict:", self.board_artist_id_map)

    def get_store(self):
        return STORE.EAGLE

    def post_add_from_path(self, post: Post, path: str):
        if (
            post.board not in self.board_artist_id_map
            or post.artist_name not in self.board_artist_id_map[post.board]
        ):
            self.create_board_and_artist_folders(
                post.board,
                [
                    post.artist_name,
                ],
            )

        artist_folder = self.board_artist_id_map[post.board][post.artist_name]
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

    def eagle_item_to_post(
        self, item: EagleItem.Item, artist_name=None, artist_board=BOARD.OTHER
    ) -> Post | None:
        pid = Post.parse_id(item.name)
        lib = self.library_path_dict[self.library]
        board_path = Path(os.path.join(lib, "images", f"{item.id}.info"))
        thumbnail = ""
        file = f"{self.library_path_dict[self.library]}/images/{item.id}.info/{item.name}.{item.ext}"
        for path in board_path.iterdir():
            strpath = str(path)
            if "metadata.json" in strpath:
                continue
            if "thumbnail" in strpath:
                thumbnail = strpath
            else:
                file = strpath

        post = PostFile(
            id=pid,
            ext_id=item.id,  # External ID
            store=self.get_store(),
            board=None,
            preview=thumbnail,
            thumbnail=thumbnail,
            file=f"{self.library_path_dict[self.library]}/images/{item.id}.info/{item.name}.{item.ext}",
        )
        return post

    def create_board_and_artist_folders(self, board: BOARD, artists: list[str]):
        self.get_artists_folder()
        for artist in artists:
            self.make_board_artist_dir(board, artist)

    def make_board_artist_dir(self, board: BOARD, artist: str) -> dict[str, Post]:
        board_name = f"{board}"
        folder_created = False
        # Create board folder if not exists
        if board not in self.board_id_map:
            board_folder = self.client.folder.create(board, self.get_artists_folder().id)
            self.board_id_map[board_folder.name] = board_folder.id
            folder_created = True
        # Create board folder if not exists
        if artist not in self.board_artist_id_map[board]:
            artist_folder = self.client.folder.create(artist, self.board_id_map[board_name])
            self.board_artist_id_map[board][artist] = artist_folder.id
            self.id_artist_map[artist_folder.id] = artist
            folder_created = True
        return folder_created

    # Assuming that we will always call get_posts before save_posts
    def get_posts(self, board: BOARD, artist: str) -> dict[str, PostFile]:
        if self.make_board_artist_dir(board, artist):
            return {}

        data = self.get_list_items(folders=self.board_artist_id_map[board][artist])
        post_files = {}
        for item in data:
            post_file = self.eagle_item_to_post(item)
            if post_file:
                post_files[post_file.id] = post_file
        logger.debug(f"Eagle Items for {board}, {artist} - {len(post_files)}")
        return post_files

    def save_post(
        self, post: Post, link_cache: Link_Cache, event: Event = None
    ) -> str | None:
        if event and event.is_set():
            return

        if link_cache:
            # loading(link_cache.increment_store_count(self.get_store())/link_cache.get_store_missing(self.get_store()))
            response = self.post_add_from_path(
                post, link_cache.get_file_from_link(post.url)
            )
        else:
            suffix = f".{post.url.split('.')[-1]}"
            with tempfile.NamedTemporaryFile(mode="wb", suffix=suffix) as f:
                Link_Cache.download_link_to_file(post.url, tempfile)
                response = self.post_add_from_path(post, f.name)
        response.raise_for_status()
        return response

    def update_post(self, post: Post):
        self.client.item.update(post.ext_id, post.tags, url=post.url)

    def get_artists_folder(self) -> EagleFolder.ListFolder:
        if self._artist_folder is not None:
            return self._artist_folder.id
        for folder in self.client.folder.list():
            if folder.name == self.artists_folder_name:
                artists_folder = folder
                break

        if not artists_folder:
            logger.info("Creating Artists (Main Parent) Folder: %s", self.artists_folder_name)
            self._artist_folder = self.client.folder.create(self.artists_folder_name)

        logger.info("Artist Folder ID: %s", artists_folder.id)
        for board_folder in artists_folder.children:
            board_name = board_folder.name
            self.board_id_map[board_name] = board_folder.id
            self.board_artist_id_map[board_name] = {}
            for artist in board_folder.children:
                artist_name = artist.name
                self.board_artist_id_map[board_name][artist_name] = artist.id
                self.id_artist_map[artist.id] = artist_name

    def switch_libary(self, library_string):
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
from asyncio import Event
from collections import defaultdict
from enum import StrEnum, auto
import os
import shutil
from typing import Iterable
from pathlib import Path, PureWindowsPath

from PIL import Image
from artrefsync.stores.link_cache import LinkCache
from artrefsync.stores.storage import ImageStoreHandler
from artrefsync.constants import APP, BOARD, LOCAL, STORE, TABLE
from artrefsync.boards.board_handler import Post, PostFile
from artrefsync.config import config
from artrefsync.utils.utils import str_dict

import logging

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


class DIRS(StrEnum):
    FILE = auto()
    PREVIEW = ".previews"
    SAMPLE = ".sample"
    THUMBNAIL = ".thumbnail"

def main():
    pass


class PlainLocalStorage(ImageStoreHandler):
    def __init__(self):
        logger.info("Plain File Store Handler Init Start")
        self.artist_base_folder = Path.cwd() / f"{config[TABLE.LOCAL][LOCAL.ARTIST_DIR]}"
        print(self.artist_base_folder.absolute())
        self.dir_base_map = {}
        self._dir_map: dict[DIRS, dict[BOARD, dict[str, str]]] = str_dict(str_dict)
        self.dir_board_folder_map = str_dict(str_dict)
        self.update_map: dict = {}
        self.folder_id_file_map: dict = defaultdict(dict)
        self.dir_base_map[DIRS.FILE] = self.artist_base_folder
        self._artist_name_map = {}
        self._ignore_list = ["(", ")", "[", "]", ",", ";", "<", ">", "="]

        for dir in DIRS:
            if dir is not DIRS.FILE:
                self.dir_base_map[dir] = self.artist_base_folder / dir.value
            dir_path = self.dir_base_map[dir]
            os.makedirs(dir_path, exist_ok=True)
            for board in BOARD:
                board_path =  dir_path / board.value
                os.makedirs(board_path, exist_ok=True)
                self._dir_map[dir][board] = {}
                # self._dir_map[dir][board][board] = board_path
                self.dir_board_folder_map[dir][board] = board_path

                for artist_path in board_path.iterdir():
                    if artist_path.is_file():
                        continue
                    update_time = os.path.getmtime(artist_path)
                    artisttxt = artist_path /  "artist.txt"
                    if os.path.exists(artisttxt):
                        with open(artisttxt, 'rt') as f:
                            artist = f.readline()
                    else:
                        artist = artist_path.name
                    self._dir_map[dir][board][artist] = artist_path
                    self.update_map[artist_path] = update_time
                    for file in artist_path.iterdir():
                        if not file.is_file() or file.name == "artist.txt":
                            continue
                        pid = file.name.rsplit(".", maxsplit=1)[0].split("-")[0]
                        if not pid:
                            continue
                        self.folder_id_file_map[artist_path][pid] = file
        logger.info("Plain File Store Handler Init Complete")


    def get_artist_posts(self, dir, board, artist) -> dict[str, str]:
        artist_dir:Path = self.get_dir_board_artist_folder(dir, board, artist)
        update_time = os.path.getmtime(artist_dir)
        last_updated = (
            self.update_map[artist_dir] if artist_dir in self.update_map else None
        )

        if artist_dir in self.update_map:
            if update_time == last_updated:
                return self.folder_id_file_map[artist_dir]

        for file in artist_dir.resolve().iterdir():
        # for file in artist_dir.iterdir():
            pid = file.name.rsplit(".", maxsplit=1)[0].split("-")[0]
            if not pid or pid == "artist":
                continue
            self.folder_id_file_map[artist_dir][pid] = file.resolve()
        self.update_map[artist_dir] = update_time
        return self.folder_id_file_map[artist_dir]

    def get_dir_board_folder(self, dir:DIRS, board:BOARD):

        if dir not in self.dir_base_map:
            if dir is DIRS.FILE:
                dir_folder = self.artist_base_folder
            else:
                dir_folder = self.artist_base_folder / dir
            os.makedirs(dir_folder, exist_ok=True)
            self.dir_base_map[dir] = dir_folder
        if board not in self.dir_board_folder_map[dir]:
            board_folder = self.dir_base_map[dir] / board
            os.makedirs(board_folder, exist_ok=True)
            self.dir_board_folder_map[dir][board] = board_folder

        return self.dir_board_folder_map[dir][board]
    

    def get_dir_board_artist_folder(self, dir: DIRS, board: BOARD, artist):
        if artist not in self._dir_map[dir][board]:
            dir_board_folder = self.get_dir_board_folder(dir, board)
            mapped_name = self.get_mapped_artist_name(artist)
            artist_dir = dir_board_folder / mapped_name
            os.makedirs(artist_dir, exist_ok=True)
            if mapped_name != artist:
                artist_txt = artist_dir / "artist.txt"
                # artist_txt = os.path.join(artist_dir, "artist.txt")
                with open(artist_txt, 'w+t') as f:
                    f.write(artist)
            self._dir_map[dir][board][artist] = artist_dir
        return self._dir_map[dir][board][artist]
    
    def get_mapped_artist_name(self, artist_name: str):
        if artist_name not in self._artist_name_map:
            mapped_name = artist_name
            for char in self._ignore_list:
                mapped_name = mapped_name.replace(char, "")
            mapped_name.replace("_", "")
            self._artist_name_map[artist_name] = mapped_name
        return self._artist_name_map[artist_name]

    def get_store(self) -> STORE:
        return STORE.LOCAL


    def create_board_and_artist_folders(self, board: BOARD, artists: Iterable[str]):
        logger.debug("Creating Board for %s, and artists: %s", board, artists)
        for artist in artists:
            for dir in DIRS:
                self.get_dir_board_artist_folder(dir, board, artist)

    def get_posts(self, board: BOARD, artist: str) -> list[PostFile]:
        """
        Returns a partial PostFile Object. Remaining metadata should be added using a Post object.
        """
        logger.info("Getting posts for %s, %s", board, artist)
        files: dict[str, Path] = self.get_artist_posts(DIRS.FILE, board, artist)
        previews = self.get_artist_posts(DIRS.PREVIEW, board, artist)
        samples = self.get_artist_posts(DIRS.SAMPLE, board, artist)
        thumbnails = self.get_artist_posts(DIRS.THUMBNAIL, board, artist)
        post_files = {}

        for pid, file in files.items():
            preview = previews[pid].resolve() if pid in previews else ""
            sample = samples[pid].resolve() if pid in samples else ""
            thumbnail = thumbnails[pid].resolve() if pid in thumbnails else ""
            ext = str(file.suffix)[1:]
            post_file = PostFile(
                id=pid,
                ext_id=str(file.resolve()),
                ext=ext,
                store=self.get_store(),
                board=board,
                artist_name=artist,
                file=str(file.resolve()),
                preview=str(preview),
                sample=str(sample),
                thumbnail=str(thumbnail),
            )
            post_files[pid] = post_file
        logger.info("Returning %d posts for %s, %s", len(post_files), board, artist)
        return post_files


    def update_thumbnails(self, board: BOARD, artist:str):
        logger.debug("Updating thumbnails for %s", artist)
        thumb_width = float(config[TABLE.APP][APP.THUMBNAIL_WIDTH])
        thumb_height = float(config[TABLE.APP][APP.THUMBNAIL_HEIGHT])
        posts = self.get_posts(board, artist)
        thumb_dir = self.get_dir_board_artist_folder(DIRS.THUMBNAIL, board, artist)
        for pid, post in posts.items():
            thumbnail_flag = False
            if post.thumbnail == "":
                thumbnail_flag = True
            else:
                try:
                    with Image.open(post.thumbnail) as img:
                        if img.width != thumb_width and img.height != thumb_height:
                            thumbnail_flag = True
                except Exception:
                    thumbnail_flag = True
            if not thumbnail_flag:
                continue

            file_name = f"{post.id}-thumbnail.{post.ext}"
            file_path = thumb_dir /  file_name
            logger.debug("Creating thumbnail for %s. path name: %s", pid, file_path)

            if post.ext == "mp4" or post.ext == "webm":
                continue

            with Image.open(post.file) as img:
                img.thumbnail(size=(thumb_width, thumb_height))
                img.save(file_path)
        logger.debug("Updating thumbnails FINISHED for %s", artist)
    
    def save_post(
        self, post: Post, link_cache: LinkCache, event: Event = None
    ) -> Post | None:
        if event and event.is_set():
            return
        saved_posts = {}
        for dir in DIRS:
            saved_posts[dir] = str(self.save_link(post, link_cache, dir))

        post_file = PostFile(
            id=post.id,
            ext_id=post.ext,
            store=self.get_store(),
            board=post.board,
            artist_name=post.artist_name,
            height=post.height,
            width=post.width,
            ratio=post.ratio,
            ext=post.ext,
            preview=saved_posts.get(DIRS.PREVIEW, ""),
            thumbnail=saved_posts.get(DIRS.THUMBNAIL, ""),
            sample=saved_posts.get(DIRS.SAMPLE, ""),
            file=saved_posts.get(DIRS.FILE, "")
        )
        return post_file


    def save_link(self, post: Post, link_cache, dir=DIRS) -> bool:
        pid = post.id
        link = ""
        suffix = ""
        match (dir):
            case DIRS.FILE:
                link = post.file_link
            case DIRS.SAMPLE:
                link = post.sample_link
                suffix = "-sample"
            case DIRS.PREVIEW:
                link = post.preview_link
                suffix = "-preview"
        if not link:
            logger.debug("Skipping downloading %s for %s. No link.", dir.value, pid)
            return ""

        file_dir = self.get_dir_board_artist_folder(
            dir=dir, board=post.board, artist=post.artist_name
        )
        link_ext = link.split(".")[-1]
        file_name = f"{pid}{suffix}.{link_ext}"
        file_path = file_dir /  file_name

        if os.path.exists(file_path):
            logger.debug(
                "Skipping downloading %s for %s. Already exists.", dir.value, pid
            )
            return file_path
        temp_thumbnail = link_cache.get_file_from_link(link)
        shutil.copy2(temp_thumbnail, file_path)
        self.folder_id_file_map[file_dir][post.id] = file_path
        return file_path

    get_thumbnail_order = [DIRS.THUMBNAIL, DIRS.PREVIEW, DIRS.SAMPLE, DIRS.FILE]

    def get_thumbnail(self, post):
        for dir in self.get_thumbnail_order:
            posts = self.get_artist_posts(dir, post.board, post.artist_name)
            if post.id in posts:
                return posts[post.id]
        return ""

    def update_post(self, board: BOARD, post: Post):
        logger.warning(
            "Update post called for  %s but this method is not implemented yet.",
            post.id,
        )
        # No Metadata is saved...right?
        pass


if __name__ == "__main__":
    main()

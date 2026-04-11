import json
import logging
import dacite
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from artrefsync.api.eagle_model import EagleFolder, EagleItem, EagleLibrary
from artrefsync.constants import STORE, EAGLE
from artrefsync.config import config
import threading

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)

def main():
    EagleClient()
    pass


class EagleClient:
    def __init__(self):
        eagle_url = config[STORE.EAGLE][EAGLE.ENDPOINT].strip()
        self.eagle_url = eagle_url if eagle_url else "http://localhost:41595/api"
        self.lock = threading.Lock()
        self.folder = self._Folder(self.eagle_url, self.lock)
        self.item = self._Item(self.eagle_url, self.lock)
        self.library = self._Library(self.eagle_url, self.lock)

    class _Folder:
        def __init__(self, eagle_url, lock):
            self.eagle_url = eagle_url
            self.lock = lock
            self.folder_timeout = 5

        def folder_url(self, folder_path) -> str:
            return f"{self.eagle_url}/folder/{folder_path}"

        @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1))
        def create(
            self, folderName: str, parent: str = None
        ) -> EagleFolder.CreatedFolder:
            data = {
                k: v
                for k, v in {"folderName": f"{folderName}", "parent": parent}.items()
                if v is not None
            }
            with self.lock:
                response = requests.post(
                    self.folder_url("create"), data=json.dumps(data), timeout=self.folder_timeout
                )
            created_file = dacite.from_dict(
                EagleFolder.CreatedFolder, json.loads(response.content)["data"]
            )
            return created_file

        # If no args given, returns info on folder id
        
        @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1))
        def update(
            self,
            folderId: str,
            newName: str = None,
            newDescription: str = None,
            newColor: str = None,
        ) -> EagleFolder.UpdatedFolder:
            data = {
                k: v
                for k, v in {
                    "folderId": folderId,
                    "newName": newName,
                    "newDescription": newDescription,
                    "newColor": newColor,
                }.items()
                if v is not None
            }

            with self.lock:
                response = requests.post(
                    self.folder_url("update"), data=json.dumps(data), timeout=self.folder_timeout
                )
            response.raise_for_status()
            data = json.loads(response.content)["data"]
            updated_item = dacite.from_dict(EagleFolder.UpdatedFolder, data)
            return updated_item

        @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1))
        def list(self) -> list[EagleFolder.ListFolder]:
            with self.lock:
                response = requests.get(self.folder_url("list"), timeout=self.folder_timeout).content
            data = json.loads(response)["data"]
            folder_list = [
                dacite.from_dict(EagleFolder.ListFolder, item) for item in data
            ]
            return folder_list

    class _Library:
        def __init__(self, eagle_url, lock):
            self._library_url = f"{eagle_url}/library"
            self.lock = lock
            self.library_timeout = 5

        def library_url(self, library_path):
            return f"{self._library_url}/{library_path}"

        def info(self) -> EagleLibrary.Info:
            logger.info("Getting Library Info...")
            with self.lock:
                response = requests.get(self.library_url("info"), timeout=self.library_timeout)
            response.raise_for_status()
            data = json.loads(response.content)["data"]
            return dacite.from_dict(EagleLibrary.Info, data)

        def history(self) -> list[str]:
            logger.info("Getting Library History...")
            with self.lock:
                response = requests.get(self.library_url("history"), timeout=self.library_timeout)
            response.raise_for_status()
            data = json.loads(response.content)["data"]
            data = [x.replace("\\", "/").removesuffix("/") for x in data]
            logger.info("history: %s", data)
            return data

        def switch(self, library_path: str) -> str:
            data = {"libraryPath": library_path}
            with self.lock:
                response = requests.post(
                    self.library_url("switch"), data=json.dumps(data), timeout=self.library_timeout
                )
            response.raise_for_status()
            content = json.loads(response.content)
            return content

    class _Item:
        def __init__(self, eagle_url, lock):
            self._item_url = f"{eagle_url}/item"
            self.lock = lock
            self.item_timeout = 5

        def item_url(self, item_path) -> str:
            return f"{self._item_url}/{item_path}"

        @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1))
        def thumbnail(self, pid) -> EagleItem.UpdatedItem:
            with self.lock:
                response = requests.get(
                    f"{self.item_url('thumbnail')}?id={pid}", timeout=self.item_timeout
                )
            data = json.loads(response.content)["data"]
            return data

        @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1))
        def info(self, pid) -> EagleItem.UpdatedItem:
            with self.lock:
                response = requests.get(f"{self.item_url('info')}?id={pid}", timeout=self.item_timeout)
            response.raise_for_status()
            data = json.loads(response.content)["data"]
            info = dacite.from_dict(EagleItem.UpdatedItem, data)
            return info

        @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1))
        def update(
            self,
            pid: str,
            tags: list[str] = None,
            annotation: str = None,
            url: str = None,
            star: int = None,
        ) -> EagleItem.UpdatedItem:
            data = {
                k: v
                for k, v in {
                    "id": pid,
                    "tags": tags,
                    "annotation": annotation,
                    "url": url,
                    "star": star,
                }.items()
                if v is not None
            }

            with self.lock:
                response = requests.post(
                    self.item_url("update"), data=json.dumps(data), timeout=self.item_timeout
                )
            response.raise_for_status()
            data = json.loads(response.content)["data"]
            updated_item = dacite.from_dict(EagleItem.UpdatedItem, data)
            return updated_item

        def post_add_from_path(
            self,
            path: str,
            name: str,
            website: str = None,
            annotation: str = None,
            tags: list[str] = None,
            folder_id: str = None,
        ) -> requests.Response:
            data = {
                k: v
                for k, v in {
                    "path": path,
                    "name": name,
                    "website": website,
                    "annottion": annotation,
                    "tags": tags,
                    "folderId": folder_id,
                }.items()
                if v is not None
            }

            with self.lock:
                response = requests.post(
                    self.item_url("addFromPath"), data=json.dumps(data), timeout=self.item_timeout
                )
            response.raise_for_status()
            data = json.loads(response.content)["data"]
            return data

        def moveToTrash(self, trash_id_list: list[str]) -> requests.Response:
            data = {"itemIds": trash_id_list}
            with self.lock:
                response = requests.post(
                    "http://localhost:41595/api/item/moveToTrash",
                    data=json.dumps(data),
                    timeout=5,
                )
            response.raise_for_status()
            return response.status_code

        def list_items(
            self,
            limit=10000,
            offset=0,
            order_by=None,
            keyword=None,
            ext=None,
            tags=None,
            folders=None,
        ) -> list[EagleItem.Item]:
            data = [
                f"{k}={v if not isinstance(v, list) else ','.join(v)}"
                for k, v in {
                    "limit": limit,
                    "offset": offset,
                    "orderBy": order_by,
                    "keyword": keyword,
                    "ext": ext,
                    "tags": tags,
                    "folders": folders,
                }.items()
                if v
            ]
            request = f"{self.item_url('list')}?{'&'.join(data)}"

            with self.lock:
                response = requests.get(request, timeout=5)
            response.raise_for_status()
            data = json.loads(response.content)["data"]
            list_items = [dacite.from_dict(EagleItem.Item, item) for item in data]
            return list_items

if __name__ == "__main__":
    main()

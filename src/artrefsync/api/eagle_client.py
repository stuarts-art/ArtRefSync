from concurrent.futures import ThreadPoolExecutor
import json
import concurrent
import time
import dacite
import requests
from artrefsync.api.eagle_model import EagleFolder, EagleItem, EagleLibrary
from artrefsync.constants import *
from artrefsync.config import config
from artrefsync.utils.benchmark import Bm
import threading


class __EagleClient:
    def __init__(self):
        eagle_url = config[STORE.EAGLE][EAGLE.ENDPOINT].strip()
        self.eagle_url = eagle_url if eagle_url else "http://localhost:41595/api"
        self.eagle_url = eagle_url if eagle_url else "http://localhost:41595/api"
        self.lock = threading.Lock()
        self.folder = self._Folder(self.eagle_url, self.lock)
        self.item = self._Item(self.eagle_url, self.lock)
        self.library = self._Library(self.eagle_url, self.lock)

    class _Folder:
        def __init__(self, eagle_url, lock):
            self.eagle_url = eagle_url
            self.lock = lock

        def folder_url(self, folder_path) -> str:
            return f"{self.eagle_url}/folder/{folder_path}"

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
                    self.folder_url("create"), data=json.dumps(data)
                )

            created_file = dacite.from_dict(
                EagleFolder.CreatedFolder, json.loads(response.content)["data"]
            )

            return created_file

        # If no args given, returns info on folder id
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
                    self.folder_url("update"), data=json.dumps(data), timeout=5
                )
            response = json.loads(response.content)["data"]
            with open("scratch/eagle_client_testing.json", "w") as f:
                json.dump(response, f, indent=4)

            updated_item = dacite.from_dict(EagleFolder.UpdatedFolder, response)
            return updated_item

        def list(self) -> list[EagleFolder.ListFolder]:
            with self.lock:
                response = json.loads(
                    requests.get(self.folder_url("list"), timeout=5).content
                )
            # print(response)
            response = response["data"]
            with open("scratch/eagle_client_testing_list.json", "w") as f:
                json.dump(response, f, indent=4)
            folder_list = [
                dacite.from_dict(EagleFolder.ListFolder, item) for item in response
            ]
            return folder_list

    class _Library:
        def __init__(self, eagle_url, lock):
            self._library_url = f"{eagle_url}/library"
            self.lock = lock

            # response = requests.get("http://localhost:41595/api/library/history")

        def library_url(self, library_path):
            return f"{self._library_url}/{library_path}"

        def info(self) -> EagleLibrary.Info:
            with self.lock:
                response = requests.get(self.library_url("info"), timeout=5)
            dict_response = json.loads(response.content)["data"]
            return dacite.from_dict(EagleLibrary.Info, dict_response)

        def history(self) -> list[str]:
            with self.lock:
                response = requests.get(self.library_url("history"), timeout=5)
            # data = json.loads(response.content)["data"]
            data = json.loads(response.content)["data"]
            data = [x.replace("\\", "/").removesuffix("/") for x in data]
            return data

        def switch(self, library_path: str) -> str:
            data = {"libraryPath": library_path}
            with self.lock:
                response = requests.post(
                    self.library_url("switch"), data=json.dumps(data), timeout=5
                )
            # print(response)
            return json.loads(response.content)

    class _Item:
        def __init__(self, eagle_url, lock):
            self._item_url = f"{eagle_url}/item"
            self.lock = lock

        def item_url(self, item_path) -> str:
            return f"{self._item_url}/{item_path}"

        def thumbnail(self, pid) -> EagleItem.UpdatedItem:
            with self.lock:
                response = requests.get(
                    f"{self.item_url('thumbnail')}?id={pid}", timeout=5
                )
            response = json.loads(response.content)["data"]
            return response

        def info(self, pid) -> EagleItem.UpdatedItem:
            with self.lock:
                response = requests.get(f"{self.item_url('info')}?id={pid}", timeout=5)
            response = json.loads(response.content)["data"]
            info = dacite.from_dict(EagleItem.UpdatedItem, response)
            return info

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
                    self.item_url("update"), data=json.dumps(data), timeout=5
                )
            response = json.loads(response.content)["data"]

            with open("scratch/eagle_client_update_testing.json", "w") as f:
                json.dump(response, f, indent=4)

            updated_item = dacite.from_dict(EagleItem.UpdatedItem, response)
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
                    self.item_url("addFromPath"), data=json.dumps(data), timeout=5
                )
            return response

        def moveToTrash(self, trash_id_list: list[str]) -> requests.Response:
            data = {"itemIds": trash_id_list}
            with self.lock:
                response = requests.post(
                    "http://localhost:41595/api/item/moveToTrash",
                    data=json.dumps(data),
                    timeout=5,
                )
            return response

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
            response = json.loads(response.content)["data"]
            list_items = [dacite.from_dict(EagleItem.Item, item) for item in response]
            return list_items


eagle_client = __EagleClient()
# items = eagle_client.item.list_items(tags="diives")
# print(items)
# update = eagle_client.item.update("MJ3YKTSRKO6N0", ["test2"])
# print(update)
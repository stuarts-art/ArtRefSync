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


class __EagleClient:
    def __init__(self):
        eagle_url = config[STORE.EAGLE][EAGLE.ENDPOINT].strip()
        self.eagle_url = eagle_url if eagle_url else "http://localhost:41595/api"
        self.folder = self._Folder(self.eagle_url)
        self.item = self._Item(self.eagle_url)
        self.library = self._Library(self.eagle_url)

    class _Folder:
        def __init__(self, eagle_url):
            self.eagle_url = eagle_url

        def folder_url(self, folder_path) -> str:
            return f"{self.eagle_url}/folder/{folder_path}"

        def create(self, folderName: str, parent: str = None) -> EagleFolder.CreatedFolder:
            data = {
                k: v
                for k, v in {"folderName": folderName, "parent": parent}.items()
                if v is not None
            }
            response = requests.post(self.folder_url("create"), data=json.dumps(data))

            created_file = dacite.from_dict(EagleFolder.CreatedFolder, json.loads(response.content)["data"])


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

            response = requests.post(
                self.folder_url("update"), data=json.dumps(data), timeout=5
            )
            response = json.loads(response.content)["data"]
            with open("scratch/eagle_client_testing.json", 'w') as f:
                json.dump(response, f, indent=4)

            updated_item = dacite.from_dict(EagleFolder.UpdatedFolder, response)
            return updated_item

        def list(self) -> list[EagleFolder.ListFolder]:
            response = json.loads(requests.get(self.folder_url("list"), timeout=5).content)
            # print(response)
            response = response["data"]
            with open("scratch/eagle_client_testing_list.json", 'w') as f:
                json.dump(response, f, indent=4)
            folder_list = [dacite.from_dict(EagleFolder.ListFolder, item) for item in response]
            return folder_list


    class _Library:
        def __init__ (self, eagle_url):
            self._library_url = f"{eagle_url}/library"

            # response = requests.get("http://localhost:41595/api/library/history")

        def library_url (self, library_path):
            return f"{self._library_url}/{library_path}"
        
        def info(self) -> EagleLibrary.Info:
            response = requests.get(self.library_url("info"), timeout=5)
            dict_response = json.loads(response.content)["data"]
            return dacite.from_dict(EagleLibrary.Info, dict_response)

        def history(self) -> list[str]:
            response =  requests.get(self.library_url("history"), timeout=5)
            # data = json.loads(response.content)["data"]
            data = json.loads(response.content)["data"]
            data = [x.replace('\\', '/').removesuffix('/') for x in data]
            return data

        def switch(self, library_path:str) -> str:
            data = {"libraryPath": library_path}
            response = requests.post(self.library_url("switch"), data=json.dumps(data), timeout=5)
            print(response)
            return json.loads(response.content)
            


    class _Item:
        def __init__(self, eagle_url):
            self._item_url = f"{eagle_url}/item"

        def item_url(self, item_path) -> str:
            return f"{self._item_url}/{item_path}"

            
        
        def info(self, pid) -> EagleItem.UpdatedItem:
            response = requests.get(f"{self.item_url("info")}?id={pid}",timeout=5)
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
        ) -> requests.Response:
            data = {
                k: v
                for k, v in {
                    "id": pid,
                    "tags": tags,
                    "annotation": annotation,
                    "url": url,
                    "star": star
                }.items()
                if v is not None
            }

            response = requests.post(
                self.item_url("update"), data=json.dumps(data), timeout=5
            )
            response = json.loads(response.content)["data"]
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

            response = requests.post(
                self.item_url("addFromPath"), data=json.dumps(data), timeout=5
            )
            return response

        def moveToTrash(self, trash_id_list: list[str]) -> requests.Response:
            data = {"itemIds": trash_id_list}
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
                f"{k}={v if not isinstance(v, list) else ",".join(v)}"
                for k, v in {
                    "limit": limit,
                    "offset": offset,
                    "orderBy": order_by,
                    "keyword": keyword,
                    "ext": ext,
                    "tags": tags,
                    "folders": folders,
                }.items() if v
            ]
            request = f"{self.item_url("list")}?{"&".join(data)}"

            response = requests.get(request, timeout=5)
            response = json.loads(response.content)["data"]
            list_items = [dacite.from_dict(EagleItem.Item, item) for item in response]
            return list_items

eagle_client = __EagleClient()


# TODO: Move to test file.
def _test_lib():
    # info = client.library.info()
    history = eagle_client.library.history()
    print(history)


def _test_folder():
    client = __EagleClient()
    folder_list = client.folder.list()
    children_list:list[EagleFolder.ListFolder] = []
    level_list:list[int] = []
    for folder in folder_list:
        level_list.append(0)
        children_list.append(folder)

    while(children_list):
        level = level_list.pop()
        curr = children_list.pop()
        for child in curr.children:
            level_list.append(level + 1)
            children_list.append(child)


def _test_item():
    client = __EagleClient()
    l = client.item.list_items(10)
    
    r = client.item.update("MITV5FS1JJ4C1")
    print(r)
    r = client.item.info("MITV5FS1JJ4C1")
    print(r)

def _test_create():
    client = __EagleClient()
    c = client.folder.create("TestFolder")
    print(c)

def _test_update_folder():
    client = __EagleClient()

    with Bm("Folder List"):

        u = client.folder.update("MGK5D05I1PQFZ")
        # folder_list = client.folder.list()
        # print(u)
        folder_id_map = {}
        id_folder_map = {}
        post_map = {}
        total_count = u.descendantImageCount
        for board in u.children:
            u.descendantImageCount
            for child in board.children:
                folder_id_map[child.name] = child.id
                id_folder_map[child.id] = child.name

        # with ThreadPoolExecutor(max_workers=3) as executor:
        with ThreadPoolExecutor() as executor:
            # futures = [executor.submit((lambda x: (2*x,time.sleep(1),x)), fid) for fid in folder_id_map]
            futures = [executor.submit((lambda x: (x, len(client.item.list_items(folders=folder_id_map[x])))), fid) for fid in folder_id_map]
            for future in concurrent.futures.as_completed(futures):
                print(future.result())
                # post_list : list[EagleItem.Item] = future.result()
        #         for post in post_list:
        #             post_map[post.id] = post
        # print(post_map)
    
    with Bm("Test singular call"):
        folder_str = ",".join(id_folder_map.keys())
        
        posts = []
        with ThreadPoolExecutor() as executor:
            futures=[]
            for i in range(total_count// 1000):
                futures.append(executor.submit(lambda: (client.item.list_items( limit =1000, offset=i, folders=folder_str))))

            for future in concurrent.futures.as_completed(futures):
                results = future.result()
                print(len(results))
                posts.extend(results)



    with Bm("Synchronous for loop"):

        items = []
        for i in range(total_count// 1000):
            items.extend(client.item.list_items( limit =1000, offset=i, folders=folder_str))

        

        

    

if __name__ == "__main__":
    client = __EagleClient()
    # _test_update_folder()
    # _test_create()
    # _test_lib()
    # _test_item()
    # _test_folder()
    dir = "MGK5D05I1PQFZ"
    l = client.item.list_items(folders= dir)
    print(l)

    # print("Done.")

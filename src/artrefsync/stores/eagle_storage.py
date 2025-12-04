from collections import deque
import queue
import requests
import json
from urllib import parse
from artrefsync.stores.storage import ImageStorage, Post
from artrefsync.constants import BOARD, EAGLE, STORE, STATS
import artrefsync.stats as stats

def main():

    config = {STORE.EAGLE: {
        EAGLE.LIBRARY: "",
        EAGLE.ARTIST_FOLDER: "artists",
        EAGLE.ENDPOINT: ""
    }}
    eagle = EagleHandler(config)
    print(eagle.artists_id)
    print(eagle.board_dict)
    print(eagle.board_artist_dict)
    # output = eagle.post_create_folder("test2", eagle.board_dict[BOARD.E621])
    print(eagle.board_artist_dict[BOARD.E621]["diives"])
    print(eagle.get_posts(BOARD.E621, "diives"))


class EagleHandler(ImageStorage):
    """
    Helper class for interacting with Eagle using https://api.eagle.cool/
    """
    def __init__(self, config):
        self.library = config[STORE.EAGLE][EAGLE.LIBRARY].strip()
        self.artists_folder_name = config[STORE.EAGLE][EAGLE.ARTIST_FOLDER].strip()
        eagle_url = config[STORE.EAGLE][EAGLE.ENDPOINT].strip()
        self.eagle_url = eagle_url if eagle_url else "http://localhost:41595/api"
        self.artists_id = None
        self.board_dict = {}
        self.board_artist_dict = {}

        if self.artists_folder_name == "":
            self.artists_folder_name = "artists"
        
        self.switch_libary(self.library)
        
        self.get_or_create_artist_folder()
        print(self.artists_id)
        print("\n")
        print(self.board_dict)
        print("\n")
        print(self.board_artist_dict)
        print("\n")
    
    def get_store(self):
        return STORE.EAGLE
    
    def post_create_folder(self, folder_name, parent_id)->dict:
        data = {
            "folderName": folder_name,
            "parent": parent_id
        }
        try:
            response = requests.post("http://localhost:41595/api/folder/create", data=json.dumps(data))
            return json.loads(response.content)["data"]
        except Exception as e:
            print("Failed to create folder for {folder_name} with parent {parent_id}")
            print(e)
            stats.add(STATS.FAILED_COUNT, 1)
            return {}

    def get_list_items(self, limit=None, offset=None, folders = None):
        eagle_url = f"http://localhost:41595/api/item/list"
        suffix = []
        if limit:
            suffix.append(f"limit={limit}")
        if offset:
            suffix.append(f"offset={offset}")
        if folders:
            suffix.append(f"folders={folders}")
        suffix = "&".join(suffix)
        if len(suffix) > 0:
            eagle_url = f"{eagle_url}?{suffix}"
        
        print(eagle_url)
        response = requests.get(eagle_url)
        response_dict = json.loads(response.content)["data"]
        return response_dict

    def post_update_post(self, id, tags=None, url=None):
        eagle_url = "http://localhost:41595/api/item/update"

        data = {"id": id,
                "tags": tags
                }
        if url:
            data["url"] = url
        response = requests.post(eagle_url, json.dumps(data))
        return response

    # Assuming that we will always call get_posts before save_posts
    def get_posts(self, board: BOARD, artist:str):
        folder_created = False
        # Create board folder if not exists
        if board not in self.board_dict:
            board_folder = self.post_create_folder(board, self.artists_id)
            board_name = board_folder["name"]
            self.board_dict[board_folder["name"]] = board_folder["id"]
            self.board_artist_dict[board_name] = {}
            folder_created = True

        # Create board folder if not exists
        if artist not in self.board_artist_dict[board]:
            artist_folder = self.post_create_folder(artist, self.board_dict[board])
            self.board_artist_dict[board][artist] = artist_folder["id"]
            folder_created = True
        
        if folder_created:
            return {}
        
        limit = 1000
        data = []
        for offset in range(100):
            list_items = self.get_list_items(limit, offset, self.board_artist_dict[board][artist])
            data.extend(list_items)
            if (len(list_items) < limit):
                break

        items = {}
        for item in data:
            name = str(item["name"].split('-')[0]).zfill(8)
            items[name] = item["id"]

        print (f" Eagle Items: {len(items)}")
        return items
            

    def save_post(self, post: Post):
        artist_folder = self.board_artist_dict[post.board][post.artist_name]
        request_data = {
            "url": post.url,
            "name": post.name,
            "website": post.website,
            "tags": post.tags,
            "folderId": artist_folder
        }

        return requests.post(self.api_endpoint("item/addFromURL"), data=json.dumps(request_data))

    def update_post(self, post: Post):
        pass

        
    def get_or_create_artist_folder(self):

        response = requests.get("http://localhost:41595/api/folder/list")
        folders = json.loads(response.content)["data"]

        folder_q = deque((folder for folder in folders))
        artists_folder:dict = None
        
        while folder_q:
            folder = folder_q.popleft()
            if folder["name"] == self.artists_folder_name:
                artists_folder = folder
                break
        if not artists_folder:
            data = {
                "folderName": self.artists_folder_name,
            }
            print("Creating Folder {folderName}")
            response = requests.post("http://localhost:41595/api/folder/create", data=json.dumps(data))
            artists_folder = json.loads(response.content)["data"]
            print(response)
        self.artists_id = artists_folder["id"]
        
        for board in artists_folder["children"]:
            board_name = board["name"]
            self.board_dict[board_name] = board["id"]
            self.board_artist_dict[board_name] = {}
            for artist in board["children"]:
                artist_name = artist["name"]
                self.board_artist_dict[board_name][artist_name] = artist["id"]
            

    def get_library_dict(self):
        if not hasattr(self, "library_path_dict"):
            response = requests.get("http://localhost:41595/api/library/history")
            self.library_path_dict = {}
            
            for path in json.loads(response.content)["data"]:
                self.library_path_dict[path.split('\\')[-1]] = path
        return self.library_path_dict
    
    def switch_libary(self, library_string):
        try:
            data = {"libraryPath": self.get_library_dict()[f'{library_string}.library']}
            response = requests.post("http://localhost:41595/api/library/switch", data=json.dumps(data))
            print(response.status_code)
            print(response.content)
        except Exception as e:
            print(e)



    def api_endpoint(self, path):
        return f'{self.eagle_url}/{path}'
    
if __name__ == "__main__":
    main()
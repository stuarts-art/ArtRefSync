
from sortedcontainers import SortedSet
from artrefsync.boards.board_handler import Post
from artrefsync.utils.benchmark import Bm

from artrefsync.constants import EAGLE, STORE
from artrefsync.config import config
from artrefsync.stores.eagle_storage import eagle_handler
import logging

class TagPostManager:

    def __init__(self, name_tag_dict = None):
        self.post_id:dict[str:Post] = {}
        self.reload(name_tag_dict)
        config.subscribe_reload(self.reload)
        
    def reload(self, name_tag_dict = None):
        if not name_tag_dict:
            name_tag_dict = eagle_handler.get_post_tag_dict()

        self.post_id:dict[str:Post] = {}
        self.post_tags = {}
        self.tag_posts = {}
        self.post_set = set()
        self.tag_set = set()
        for k, v in name_tag_dict.items():
            if k not in self.tag_posts:
                self.post_tags[k] = set()
                self.post_id[k] = v
            for t in v.tags:
                if t not in self.tag_posts:
                    self.tag_posts[t] = set()
                self.post_tags[k].add(t)
                self.tag_posts[t].add(k)
        
        self.post_set = set(self.post_tags.keys())
        self.tag_set = set(self.tag_posts.keys())

    def get_tags(self, *posts):
        tag_sets = [self.post_tags[post] for post in posts if post in self.tag_set]
        return self.tag_set.intersection(tag_sets)

    # filter all valid tag posts
    def get_posts(self, tags):
        # print(f"Get Posts : {tags}")
        # post_set = SortedSet()
        # for tag in tags:
        #     print(tag)
        #     if tag in self.tag_posts:
        #         post_set.update(self.tag_posts[tag])
        # print(f"Post Count: {len(post_set)}")
        # self.post

        
        
        posts = [self.tag_posts[tag] for tag in tags if tag in self.tag_set]
        intersection = self.post_set.intersection(*posts)
        print(f"Intersection Count for {tags} is {len(intersection)}")
        return intersection


        # return post_set

        

from bidict import bidict
from artrefsync.constants import EAGLE, STORE
from artrefsync.stores.eagle_storage import EagleHandler
from artrefsync.utils.benchmark import Bm
from pyvis.network import Network
from artrefsync.config import config

import logging
logger = logging.getLogger(__name__)


class TagPostManager:
    def __init__(self, name_tag_dict = None):
        self.reload(name_tag_dict)
        
    def reload(self, name_tag_dict = None):
        if not name_tag_dict:
            eagle = EagleHandler()
            name_tag_dict = eagle.get_post_tag_dict()

        self.post_tags = {}
        self.post_id = {}
        self.tag_posts = {}
        self.post_set = set()
        self.tag_set = set()
        for k, v in name_tag_dict.items():
            if k not in self.tag_posts:
                self.post_tags[k] = set()
                self.post_id[k] = v["id"]
            for t in v["tags"]:
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
    def get_posts(self, *tags):
        posts = [self.tag_posts[tag] for tag in tags if tag in self.tag_set]
        return self.post_set.intersection(*posts)

def main():

    with Bm("Make Tag to post list dict"):
        tpm = TagPostManager()

if __name__ == "__main__":
    main()

import logging
from collections import OrderedDict, deque

logger = logging.getLogger(__name__)


class ManagedCache:  # WIP Video/Gif Viewer
    def __init__(self, max_size=50):
        self.cache = OrderedDict()
        self.deque = deque()
        self.popped = deque()
        self.max_size = 50
        self.pop_count = 0

    def __contains__(self, key):
        return key in self.cache

    def __len__(self):
        return self.cache.__len__()

    def __getitem__(self, key):
        if key in self.cache:
            if key in self.deque:
                self.deque.remove(key)
            self.deque.append(key)
        return self.cache.get(key, None)

    def __setitem__(self, key, value):
        if key in self:
            self.cache.move_to_end(key, last=False)
        self.cache[key] = value
        while len(self.deque) > self.max_size:
            rkey = self.deque.pop()
            self.popped.append(rkey)
            self.cache.pop(rkey)

            if self.pop_count % 20 == 0:
                logger.debug("Popped id: %s, total popped: %s", rkey, self.pop_count)

    def clear(self):
        self.deque.clear()
        while self.cache:
            self.cache.popitem()

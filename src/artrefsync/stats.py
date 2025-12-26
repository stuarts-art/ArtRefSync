from collections.abc import Iterable
from artrefsync.constants import STATS


# module enforced singleton

class __Stats():
    def __init__(self):
        self._stats = {}
        for stat in STATS:
            if "set" in stat:
                self._stats[stat] = set()
            else:
                self._stats[stat] = 0

    def add(self, field: STATS, value=1):
        if isinstance(value, Iterable):
            if "set" in field:
                self._stats[field].update(value)
            else:
                self._stats[field] += len(value)
                return self._stats[field]
        else:
            if "set" in field:
                self._stats[field].add(value)
            else:
                self._stats[field] += value
                return self._stats[field]

    def get(self, field: STATS, limit=None):
        if field in self._stats:
            if limit and "set" in field:
                return list(self._stats[field])[:limit]
            else:
                return self._stats[field]
        else:
            return None

    def report(self):
        print("\n")
        for stat in STATS:
            print(f"{stat} - {self.get(stat, 10)}")

stats = __Stats()

if __name__ == "__main__":
    # TODO: Move to a test
    stats.add(STATS.ARTIST_SET, "a")
    stats.add(STATS.ARTIST_SET, "a")
    stats.add(STATS.ARTIST_SET, "b")
    stats.add(STATS.ARTIST_SET, "c")
    stats.add(STATS.ARTIST_SET, "d")
    stats.add(STATS.SPECIES_SET, ["x", "y", "z"])
    stats.add(STATS.POST_COUNT, 10)

    print(stats.get(STATS.ARTIST_SET))
    print(stats.get(STATS.SPECIES_SET))
    print(stats.get(STATS.TAG_SET))
    print(stats.get(STATS.POST_COUNT))
    stats.report()

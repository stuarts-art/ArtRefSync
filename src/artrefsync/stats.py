from collections.abc import Iterable
from artrefsync.constants import STATS

# module enforced singleton
_stats = {}
for stat in STATS:
    if "set" in stat:
        _stats[stat] = set()
    else:
        _stats[stat] = 0


def add(field: STATS, value):
    if isinstance(value, Iterable):
        if "set" in field:
            _stats[field].update(value)
        else:
            _stats[field] += len(value)
    else:
        if "set" in field:
            _stats[field].add(value)
        else:
            _stats[field] += value


def get(field: STATS, limit=None):
    if field in _stats:
        if limit and "set" in field:
            return list(_stats[field])[:limit]

        else:
            return _stats[field]
    else:
        return None


def report():
    print("\n")
    for stat in STATS:
        print(f"{stat} - {get(stat, 10)}")


if __name__ == "__main__":
    # TODO: Move to a test
    add(STATS.ARTIST_SET, "a")
    add(STATS.ARTIST_SET, "a")
    add(STATS.ARTIST_SET, "b")
    add(STATS.ARTIST_SET, "c")
    add(STATS.ARTIST_SET, "d")
    add(STATS.SPECIES_SET, ["x", "y", "z"])
    add(STATS.POST_COUNT, 10)

    print(get(STATS.ARTIST_SET))
    print(get(STATS.SPECIES_SET))
    print(get(STATS.TAG_SET))
    print(get(STATS.POST_COUNT))
    report()

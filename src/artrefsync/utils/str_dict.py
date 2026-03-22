from collections import UserDict

class str_dict(UserDict):
    # This class forces keys to be strings, useful when dealing with StrEnums.
    # Why? Because if a StrEnum is a key, the string equivalent does not match that key.
    # Note that if the string is a key, the StrEnum will match.
    def __init__(self, default = None):
        self.default = default
        super().__init__()

    def __setitem__(self, key, value, /) -> None:
        super().__setitem__(str(key), value)

    def __missing__(self, key) -> None:
        if self.default is None:
            raise KeyError
        else:
            self[str(key)] = self.default()            
            return self[str(key)]

    def __getitem__(self, key):
        return super().__getitem__(str(key))
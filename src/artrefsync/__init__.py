from importlib.metadata import PackageNotFoundError, version

from artrefsync.ui.TagApp import App

try:
    __version__ = version("artrefsync")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = ["App", "__version__"]

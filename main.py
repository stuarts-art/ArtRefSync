import sys

from artrefsync.config import config
from artrefsync.ui.TagApp import ImagViewerApp
from artrefsync.stores.link_cache import LinkCache
import logging
from artrefsync.utils.TkThreadCaller import TkThreadCaller

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


try:
    app = ImagViewerApp()
    app.start()
finally:
    sys.exit()
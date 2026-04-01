import sys

from artrefsync.config import config
from artrefsync.ui.TagApp import ImagViewerApp
import logging

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


try:
    app = ImagViewerApp()
    app.start()
finally:
    sys.exit()
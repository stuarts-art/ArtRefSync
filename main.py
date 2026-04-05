import logging
import sys

from artrefsync.config import config
from artrefsync.ui.TagApp import ImagViewerApp

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


try:
    app = ImagViewerApp()
    logger.info("App init complete. Starting App.")
    app.start()
except Exception as e:
    logger.error(e)
finally:
    sys.exit()
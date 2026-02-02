from artrefsync.config import config
from artrefsync.ui.TagApp import ImagViewerApp
import logging

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)

try:
    logger.info("STARTING LOG")
    app = ImagViewerApp()
    logger.info("STARTING Main loop")
    app.mainloop()
except Exception as e:
    logger.error(e)

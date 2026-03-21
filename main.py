from artrefsync.config import config
from artrefsync.ui.TagApp import ImagViewerApp
from artrefsync.stores.link_cache import link_cache, Link_Cache
import logging

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)

try:
    with Link_Cache() as link_cache:
        logger.info("STARTING LOG")
        app = ImagViewerApp()
        logger.info("STARTING Main loop")
        app.mainloop()
except Exception as e:
    logger.error(e)

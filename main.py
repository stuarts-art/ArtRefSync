from artrefsync.config import config
from artrefsync.ui.TagApp import ImagViewerApp
from artrefsync.stores.link_cache import LinkCache
import logging

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


def main():
    with LinkCache():
        logger.info("STARTING LOG")
        app = ImagViewerApp()
        logger.info("STARTING Main loop")
        app.mainloop()

if __name__ == "__main__":
    main()
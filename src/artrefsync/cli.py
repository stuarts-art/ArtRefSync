import argparse
import logging
from artrefsync import App

logger = logging.getLogger(__name__)

def ui():
    parser = argparse.ArgumentParser(description="Support for args planned. Currently does not do anything.")
    parser.add_argument(
        "path", type=str, nargs="?", help="Path to the root of your library", default="."
    )
    parser.add_argument(
        "--config_file_name", type=str, help="", default="config"
    )
    args = parser.parse_args()
    logger.info(args)
    App().start()

if __name__ == "__main__":
    ui()
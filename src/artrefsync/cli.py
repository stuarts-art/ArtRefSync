import argparse
import logging
from pathlib import Path

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

    config_path = Path(args.path).resolve()
    config_file_name = args.config_file_name
    
    App(config_path=config_path, config_file_name=config_file_name).start()

if __name__ == "__main__":
    ui()
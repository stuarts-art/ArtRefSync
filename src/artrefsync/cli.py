import os
import argparse
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def ui():
    parser = argparse.ArgumentParser(description="A sample project script")
    parser.add_argument(
        "path", type=str, help="Path to the root of your library", default="."
    )
    args = parser.parse_args()
    print(f"ARGS: {args}")
    path = Path(args.path)

    if path.is_file():
        print("path must be a directory, not a file")
        return
    if not path.exists():
        logger.info("Creating directory")
        os.makedirs(path, mode=0o771,exist_ok=True)
    os.chdir(path)
    from artrefsync import App
    App().start()

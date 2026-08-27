import argparse
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def cli():
    parser = argparse.ArgumentParser(
        description="Support for args planned. Currently does not do anything."
    )
    parser.add_argument(
        "path",
        type=str,
        nargs="?",
        help="Path to the root of your library",
        default=".",
    )
    args = parser.parse_args()

    project_path = Path(args.path).resolve()

    from artrefsync import App
    app = App(project_path=project_path)
    app.start()


if __name__ == "__main__":
    cli()

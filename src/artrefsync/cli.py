import argparse

from artrefsync import App


def ui():
    parser = argparse.ArgumentParser(description="A sample project script")
    parser.add_argument(
        "--config_path", type=str, help="Your name", default="config/config.toml"
    )
    parser.add_argument("--age", type=int, help="Your age", default=18)
    args = parser.parse_args()
    print(args)
    App().start()

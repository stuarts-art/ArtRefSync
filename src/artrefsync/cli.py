import argparse

from artrefsync import App


def ui():
    parser = argparse.ArgumentParser(description="A sample project script")
    parser.add_argument(
        "--config_path", type=str, help="Your name", default="config/config.toml"
    )
    args = parser.parse_args()
    print(f"ARGS: {args}")
    App().start()

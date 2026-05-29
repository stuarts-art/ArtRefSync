# ArtRefSync

A image viewer and downloader for artists who make dubious art.

Key Features:

1. Syncs down image and tag information from image boards (E621, Rule34, Danbooru)
2. Maintains a local tag-to-image index which allows for fast searching
3. Provides a simple UI that supports:
    - Image gallery with tag and artist filtering
    - Image/Gif viewer with zooming to a pixel level
    - Post information for each image
    - Images can be dragged out of the application into viewing tools such as [Pureref](https://www.pureref.com/)
4. Other features that I think are cool
    - 100% local (besides when syncing). It will not harvest your data.
    - Not an electron app. It is not just a reskinned chromium browser that is probably harvesting your data.
    - It has absolutely no AI integration.
    - Tag Blacklisting: Ignores all images that include tags within the blacklist, such as `ai-generated`.

> [!WARNING]
> Supported Image boards contain both SFW and **NSFW** Works.
> Only use this tool if it is appropriate to do so and does not violate the relevant website's TOS.
> This project requires the user to provide their own API key for each site.

Motivation:

- I'm an artist and was tired of questioning if the pinterest reference image I was looking at came from generative AI.
- I find the rise of censorship and surveillance concerning.
- My ADHD can't handle the 3 seconds waiting for a website to load.

### Supported Image Boards

- E621 (Furry Art) - [How to get an API key](https://e621.net/help/api#:~:text=Authorization,an%20API%20key.)
- R34 (Western Art) - [How to get an API key](https://api.rule34.xxx/#:~:text=API%20Keys,The%20API%20key)
- Danbooru (Eastern Art) - [How to get an API key](https://danbooru.donmai.us/wiki_pages/help:api#:~:text=You%20will%20need%20an%20API%20key%20if%20you%20need%20to%20login%20using%20the%20API.%20You%20can%20generate%20an%20API%20key%20by%20visiting%20your%20user%20profile%20and%20clicking%20the%20Generate%20API%20key%20button.)

### Supported Local Storage

- [Eagle](https://en.eagle.cool/)
- Plain File System

## Quick Start

### Non-Developers - Download EXE
Download the zip file from the last [workflow](https://github.com/stuarts-art/ArtRefSync/actions/workflows/windows_pyinstaller.yml) run. Extract the zip and run the exe.

### Installing from Pip
```
pip install git+https://github.com/stuartsartcode/ArtRefSync
pip install -e .
python main.py
```

### Installing from Uv
```bash
uv init . # Creates the virtual env
uv add git+https://github.com/stuartsartcode/ArtRefSync
uv sync
uv pip install -e .
uv run main.py
```

### Running from UVX
``` bash
uvx --from git+https://github.com/stuarts-art/ArtRefSync sync_cli
```

## ROADMAP
- [ ] Fix VIdeo/gif support
- [ ] Non-Image Board Files

### Other useful commands
```bash
# exporting a requirements.txt instead of a uv.lock file.
uv export --format requirements.txt --output-file requirements.txt

# Build EXE
uv run pyinstaller --collect-all ttkbootstrap --name ArtRefSync main.py
```

## Libraries:
| Library | License | Usage |
| --- | --- | --- |
[dacite](https://github.com/konradhalas/dacite) | [MIT](https://github.com/konradhalas/dacite/blob/master/LICENSE) | Codec between dictionaries and classes
[diskcache](https://github.com/grantjenks/python-diskcache) | [Apache v2.0](https://github.com/grantjenks/python-diskcache/blob/master/LICENSE) | `sqlite3` based cache that's persistent between sessions.
[opencv-python](https://github.com/opencv/opencv-python) | [MIT](https://github.com/opencv/opencv-python/blob/4.x/LICENSE.txt) | Image processing
[pillow](https://github.com/python-pillow/Pillow) | [MIT-CMU](https://github.com/python-pillow/Pillow/blob/main/LICENSE) | Image processing and conversion to tkinter friendly formats
[requests](https://github.com/psf/requests) | [Apache v2.0](https://github.com/psf/requests/blob/main/LICENSE) | Http rest request interface
[simple-toml-configurator](https://github.com/GilbN/Simple-TOML-Configurator) | [MIT](https://github.com/GilbN/Simple-TOML-Configurator/blob/main/LICENSE) | Plain-text config file creation and management.
[sortedcontainers](https://github.com/grantjenks/python-sortedcontainers) | [Apache v2.0](https://github.com/grantjenks/python-sortedcontainers/blob/master/LICENSE) | Efficient sorted wrapper for python types
[tenacity](https://github.com/jd/tenacity) | [Apache V2.0](https://github.com/jd/tenacity/blob/main/LICENSE) | Retry Interface
[tkinterdnd2](https://github.com/pmgagne/tkinterdnd2) | [MIT](https://github.com/pmgagne/tkinterdnd2/blob/master/LICENSE) | Tkinter drag and drop support.
[ttkbootstrap](https://github.com/israel-dryer/ttkbootstrap) | [MIT](https://github.com/israel-dryer/ttkbootstrap/blob/master/LICENSE) | Modern tkinter syling.

## Dev Libraries:
| Library | License | Usage |
| --- | --- | --- |
[pyinstaller](https://github.com/pyinstaller/pyinstaller) | [GNU Gneral Public](https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt) | Build exe file
[ruff](https://github.com/astral-sh/ruff) | [MIT](https://github.com/astral-sh/ruff/blob/main/LICENSE) | Linter and formatter



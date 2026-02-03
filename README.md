# ArtRefSync

This is a tool for artists that:

1. Syncs down image and tag information from image boards (E621, Rule34, Danbooru)
2. Maintains a local tag-to-image index which allows for fast searching
3. Provides a Desktop UI for searching by tag or artist, modifying settings, and viewing media
    - Image zooming down to the pixel level!
    - Gif playing
    - Drag images out of app to copy (e.g. dragging media to PureRef)

> [!WARNING]
> Supported Image boards contain both SFW and **NSFW** Works.
> Only use this tool if it is appropriate to do so and does not violate the relevant website's TOS.
> This project requires the user to provide their own API key for each site.

Motivation:

- I'm an artist and was tired of questioning if the pinterest reference image I was looking at came from generative AI.
- I find the rise of censorship and surveillance concerning.
- My ADHD can't handle the 3 seconds waiting for a website to load.

### Supported Image Boards

- R34 ([Get your API Key](https://api.rule34.xxx/#:~:text=API%20Keys,The%20API%20key))
- E621 ([How to get an API Key](https://e621.net/help/api#:~:text=Authorization,an%20API%20key.))
- Danbooru <https://danbooru.donmai.us/wiki_pages/help:api>

### Supported Local Storage

- [Eagle](https://en.eagle.cool/)
- Plain File System

## Installation

```
pip install git+https://github.com/stuartsartcode/ArtRefSync
```

Alternatively, you can download the source and run:

```
pip install -e .
```

## Usage

- [ ] TODO: Update this section

To run the sync, use:

```python
from artrefsync.sync import sync_config
sync_config()
```

When this is first ran, if the config does not exist, it creates a `config.toml` file.
Note that the default config has everything disabled.

## Configuration

To enable R34 or E621

1. Change "enabled" from "false" to "true"
2. Add api_key (and username if e621) (see [Supported Image Boards](#supported-image-boards))
3. Add artist names
4. (Optional) Add tag blacklists to avoid.

To enable storage [local]:

1. Change "enabled" from "false" to "true"
2. (Optional) Change the artist directory.

Files will be stored as such:

```
artists/
  e621/
    artist 1
    artist 2
    artist ...
  r34/
    artist 1
    artist 2
    artist ...
```

```toml
[app]
limit = 10

[r34]
enabled = false
artists = []
black_list = []
api_key = ""

[e621]
enabled = false
artists = []
black_list = []
api_key = ""
username = ""

[eagle]
enabled = false
endpoint = "http://localhost:41595/api"
library = ""
artist_folder = ""

[local]
enabled = false
artist_folder = ""
```

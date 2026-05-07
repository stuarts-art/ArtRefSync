# ArtRefSync

This is a tool for artists that:

1. Syncs down image and tag information from image boards (E621, Rule34, Danbooru)
2. Maintains a local tag-to-image index which allows for fast searching
3. Provides a simple UI that supports:
    - Image gallery with tag and artist filtering
    - Image/Gif viewer with zooming to a pixel level
    - Post information for each image
    - Images can be dragged out of the application into viewing tools such as [Pureref](https://www.pureref.com/)
4. Other features that I think are cool
    - It is 100% local (besides when syncing). It will not harvest your data.
    - It is not an electron app. It is not just a reskinned chromium browser that is probably harvesting your data.
    - It has absoultely no AI integration.





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


## ROADMAP
- [ ] Video Support?
- [ ] Non-image board files?
- [ ] Non image files?
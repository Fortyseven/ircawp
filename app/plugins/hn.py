"""
Hacker News Front Page
"""

import datetime
from app.media_backends.MediaBackend import MediaBackend
from app.backends.Ircawp_Backend import Ircawp_Backend
from .__PluginBase import PluginBase
import feedparser


START_TIME = datetime.datetime.now()
RSS_URL = "https://hnrss.org/frontpage"


def hn(
    prompt: str,
    media: list,
    backend: Ircawp_Backend,
    media_backend: MediaBackend = None,
) -> tuple[str, str, bool]:
    url = RSS_URL
    feed = feedparser.parse(url)

    return (
        f"Top stories from Hacker News as of {START_TIME.strftime('%Y-%m-%d %H:%M:%S')}"
        + "\n".join(
            [
                f"{i + 1}. {feed.entries[i].title} - {feed.entries[i].link}"
                for i in range(5)
            ]
        ),
        "",
        False,
        {},
    )


plugin = PluginBase(
    name="Hacker News Front Page",
    description="Dumps the current front page of Hacker News.",
    triggers=["hn"],
    system_prompt="",
    emoji_prefix="",
    msg_empty_query="No prompt provided",
    msg_exception_prefix="HACKER PROBLEMS",
    main=hn,
    use_imagegen=False,
    prompt_required=False,
)

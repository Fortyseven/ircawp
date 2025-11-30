"""
Get the bot's uptime and stats.
"""

from datetime import datetime
from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend
from .__PluginBase import PluginBase


START_TIME = datetime.now()


def uptime(
    prompt: str,
    media: list,
    backend: Ircawp_Backend,
    media_backend: MediaBackend = None,
) -> tuple[str, str, bool]:
    now = datetime.now()
    uptime = now - START_TIME

    uptime = str(uptime).split(".")[0]
    start_time = START_TIME.strftime("%Y-%m-%d %H:%M:%S")

    return (
        f"""STATS:
    - Uptime: {uptime}
    - Last started: {start_time}
    - Current model: {backend.model}
    - Last query time: {backend.last_query_time or "None yet"}
    """.strip(),
        "",
        True,
    )


plugin = PluginBase(
    name="Uptime",
    description="Get the bot's uptime and stats.",
    triggers=["uptime", "stats"],
    system_prompt="",
    emoji_prefix="",
    msg_empty_query="No prompt provided",
    msg_exception_prefix="UPTIME PROBLEMS",
    main=uptime,
    use_imagegen=False,
    prompt_required=False,
)

"""
Get the bot's uptime and stats.
"""

import datetime
from backends.BaseBackend import BaseBackend
from plugins.AskBase import AskBase


START_TIME = datetime.datetime.now()


def uptime(prompt: str, backend: BaseBackend) -> tuple[str, str]:
    from datetime import datetime
    from datetime import timedelta

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
    )


plugin = AskBase(
    name="Uptime",
    description="Get the bot's uptime and stats.",
    triggers=["uptime", "stats"],
    system_prompt="",
    emoji_prefix="",
    msg_empty_query="No prompt provided",
    msg_exception_prefix="ARTISTIC PROBLEMS",
    main=uptime,
    use_imagegen=False,
    prompt_required=False,
)

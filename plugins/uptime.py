"""
Get the bot's uptime and stats.
"""
import datetime
from backends import BaseBackend


TRIGGERS = ["uptime", "stats"]
DESCRIPTION = "Get the bot's uptime and stats."
GROUP = "system"

START_TIME = datetime.datetime.now()


def execute(query: str, backend: BaseBackend) -> str:
    from datetime import datetime
    from datetime import timedelta

    now = datetime.now()
    uptime = now - START_TIME

    uptime = str(uptime).split(".")[0]
    start_time = START_TIME.strftime("%Y-%m-%d %H:%M:%S")

    return f"""STATS:
    - Uptime: {uptime}
    - Last started: {start_time}
    - Current model: {backend.model}
    - Last query time: {backend.last_query_time or "None yet"}
    """.strip()

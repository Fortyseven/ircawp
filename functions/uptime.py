import datetime
from backends import BaseBackend


TRIGGERS = ["uptime", "stats"]
DESCRIPTION = "Get the bot's uptime and stats."

# get now
START_TIME = datetime.datetime.now()


def execute(query: str, backend: BaseBackend) -> str:
    from datetime import datetime
    from datetime import timedelta

    now = datetime.now()
    uptime = now - START_TIME

    return f"""
    - Uptime: {uptime}
    - Last started: {START_TIME}
    - Current model: {backend.model}
    - Last query time: {backend.last_query_time or "None yet"}
    """.strip()

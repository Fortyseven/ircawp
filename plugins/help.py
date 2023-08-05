"""
Help command, returns a list of registered slash commands.
"""

from backends import BaseBackend

TRIGGERS = ["help", "?"]
DESCRIPTION = "Returns a list of registered slash commands."


def get_triggers(trigger: list) -> str:
    return "/" + ", /".join(trigger)


def execute(query: str, backend: BaseBackend) -> str:
    from plugins import PLUGINS  # lazy load

    return "AVAILABLE SLASH COMMANDS :\n\n" + "\n".join(
        [
            f"- `{get_triggers(PLUGINS[x].TRIGGERS)}` - {PLUGINS[x].DESCRIPTION}"
            for x in PLUGINS
            # if not PLUGINS[x].get("hide", False)
        ]
    )

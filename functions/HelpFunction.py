"""
Help function, returns a list of registered slash commands.
"""

from backends import BaseBackend

TRIGGERS = ["help", "?"]
DESCRIPTION = "Returns a list of registered slash commands."


def get_triggers(trigger: list) -> str:
    return "/" + ", /".join(trigger)


def execute(query: str, backend: BaseBackend) -> str:
    from functions import FUNCTIONS  # lazy load

    return "AVAILABLE SLASH COMMANDS :\n\n" + "\n".join(
        [
            f"- `{get_triggers(FUNCTIONS[x].TRIGGERS)}` - {FUNCTIONS[x].DESCRIPTION}"
            for x in FUNCTIONS
            # if not FUNCTIONS[x].get("hide", False)
        ]
    )

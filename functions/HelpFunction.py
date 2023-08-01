"""
Help function, returns a list of registered slash commands.
"""

from backends import BaseBackend


def execute(query: str, backend: BaseBackend) -> str:
    from functions import FUNCTIONS  # lazy load

    return "AVAILABLE SLASH COMMANDS :\n\n" + "\n".join(
        [
            f'- `/{x}` - {FUNCTIONS[x]["description"]}'
            for x in FUNCTIONS
            if not FUNCTIONS[x].get("hide", False)
        ]
    )

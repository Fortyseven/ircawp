"""
Bot plugin that reverses the query string.
"""

from app.backends.Ircawp_Backend import Ircawp_Backend


TRIGGERS = ["reverse"]
DESCRIPTION = "Reverses the query string."


def execute(query: str, backend: Ircawp_Backend) -> tuple[str, str]:
    if not query:
        return "No query provided for reverse plugin.", ""

    return query[::-1], ""

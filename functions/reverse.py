"""
Bot function that reverses the query string.
"""
from backends import BaseBackend


TRIGGERS = ["reverse"]
DESCRIPTION = "Reverses the query string."

def execute(query: str, backend: BaseBackend) -> str:
    if not query:
        return "No query provided for reverse function"

    return query[::-1]

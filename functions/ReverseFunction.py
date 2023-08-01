"""
Bot function that reverses the query string.
"""
from backends import BaseBackend


def execute(query: str, backend: BaseBackend) -> str:
    if not query:
        return "No query provided for reverse function"

    return query[::-1]

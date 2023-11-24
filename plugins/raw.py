"""
Bot plugin that allows the user to ask a raw prompt of the LLM without a system preamble.
"""

from backends.BaseBackend import BaseBackend

TRIGGERS = ["raw"]
GROUP = "ask"
DESCRIPTION = "Pass a raw prompt to the LLM without a system preamble."


def execute(query: str, backend: BaseBackend) -> str:
    if not query.strip():
        return "No prompt?"

    try:
        return backend.query(query.strip(), raw=True)
    except Exception as e:
        return "RAW PROBLEMS: " + str(e)

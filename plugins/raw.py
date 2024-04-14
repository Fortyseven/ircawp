"""
Bot plugin that allows the user to ask a raw prompt of the LLM without a system preamble.
"""

from backends.BaseBackend import BaseBackend

TRIGGERS = ["raw"]
GROUP = "ask"
DESCRIPTION = "Pass a raw prompt to the LLM without a system preamble."


def execute(query: str, backend: BaseBackend) -> tuple[str, str]:
    if not query.strip():
        return "No prompt?", ""

    try:
        return backend.query(system_prompt="", user_prompt=query.strip()), ""
    except Exception as e:
        return "RAW PROBLEMS: " + str(e), ""

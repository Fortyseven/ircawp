"""
Bot plugin that allows the user to pass a raw prompt to the system imagegen backend and post a response.
"""

from backends.BaseBackend import BaseBackend

TRIGGERS = ["sdxs"]
# GROUP = "ask"
DESCRIPTION = "Pass a raw prompt to the LLM without a system preamble."


def execute(query: str, backend: BaseBackend) -> str:
    if not query.strip():
        return "No prompt?"

    try:
        # return backend.query(system_prompt="", user_prompt=query.strip())
        return "This feature is a WIP."
    except Exception as e:
        return "IMG PROBLEMS: " + str(e)

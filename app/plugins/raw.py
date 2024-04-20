"""
Bot plugin that allows the user to ask a raw prompt of the LLM without a system preamble.
"""

from app.backends.Ircawp_Backend import Ircawp_Backend
from .__AskBase import AskBase


def raw(prompt: str, backend: Ircawp_Backend) -> tuple[str, str]:
    # return prompt.strip(), ""
    return backend.query(system_prompt="", user_prompt=prompt.strip()), ""


plugin = AskBase(
    name="Raw LLM query",
    description="Pass a raw prompt to the LLM without a system preamble.",
    triggers=["raw"],
    system_prompt="",
    emoji_prefix="",
    msg_empty_query="No prompt provided",
    msg_exception_prefix="ARTISTIC PROBLEMS",
    main=raw,
    use_imagegen=False,
)

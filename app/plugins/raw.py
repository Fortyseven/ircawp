"""
Bot plugin that allows the user to ask a raw prompt of the LLM without a system preamble.
"""

from app.backends.Ircawp_Backend import Ircawp_Backend
from app.types import InfResponse
from .__PluginBase import PluginBase


def raw(prompt: str, backend: Ircawp_Backend) -> InfResponse:
    # return prompt.strip(), ""
    response = backend.runInference(system_prompt="", prompt=prompt.strip())
    return response, (), False


plugin = PluginBase(
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

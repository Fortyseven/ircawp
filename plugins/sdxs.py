"""
Bot plugin that allows the user to pass a raw prompt to the system imagegen backend and post a response.
"""

from backends.BaseBackend import BaseBackend
from plugins.AskBase import AskBase


def sdxs(prompt: str, backend: BaseBackend) -> tuple[str, str]:
    return prompt.strip(), ""


plugin = AskBase(
    name="SDXS Image Generator",
    description="Pass a raw prompt to the SDXS image generator.",
    triggers=["sdxs"],
    system_prompt="",
    emoji_prefix="",
    msg_empty_query="No prompt provided",
    msg_exception_prefix="ARTISTIC PROBLEMS",
    main=sdxs,
    use_imagegen=True,
)

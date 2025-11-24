"""
Bot plugin that allows the user to pass a raw prompt to the system imagegen backend and post a response.
"""

from app.backends.Ircawp_Backend import Ircawp_Backend
from .__PluginBase import PluginBase


def img(prompt: str, media: list, backend: Ircawp_Backend) -> tuple[str, str, bool]:
    # we don't run the imagegen here, we just pass it all back
    # to ircawp to process without inference

    return prompt.strip(), "", False


plugin = PluginBase(
    name="SDXS Image Generator",
    description="Pass a raw prompt to the SDXS image generator.",
    triggers=["sdxs"],
    system_prompt="",
    emoji_prefix="",
    msg_empty_query="No prompt provided",
    msg_exception_prefix="ARTISTIC PROBLEMS",
    main=img,
    use_imagegen=True,
)

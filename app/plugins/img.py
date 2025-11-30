"""
Bot plugin that allows the user to pass a raw prompt to the system imagegen backend and post a response.
"""

from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend
from app.lib.llm_helpers import refinePrompt
from .__PluginBase import PluginBase


def img(
    prompt: str,
    media: list,
    backend: Ircawp_Backend,
    media_backend: MediaBackend = None,
) -> tuple[str, str, bool]:
    # we don't run the imagegen here, we just pass it all back
    # to ircawp to process without inference

    if prompt[0] == "!":
        refined_prompt = prompt[1:]
        backend.console.log("[white on green] skipping prompt refinement")
    else:
        refined_prompt = refinePrompt(prompt, backend, media)

    # Clean up the refined prompt
    final_prompt = refined_prompt.strip()

    if "i'm sorry" in final_prompt.lower() or "i cannot" in final_prompt.lower():
        backend.console.log("[pink on red] prompt refinement refused, using original")
        final_prompt = prompt.strip()

    backend.console.log(f"[black on green] refined prompt: '{final_prompt}'")

    # Call media backend to generate the image
    image_path = media_backend.execute(prompt=final_prompt)

    # return "Refined prompt:\n```" + final_prompt.strip() + "```", image_path, False
    return "", image_path, False


plugin = PluginBase(
    name="Image Generator",
    description="Pass a raw prompt to the image generator.",
    triggers=["img"],
    system_prompt="",
    emoji_prefix="",
    msg_empty_query="No prompt provided",
    msg_exception_prefix="ARTISTIC PROBLEMS",
    main=img,
    use_imagegen=True,
)

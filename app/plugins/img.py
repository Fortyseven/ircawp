"""
Bot plugin that allows the user to pass a raw prompt to the system imagegen backend and post a response.
"""

import re
from typing import Dict, Any
from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend
from app.lib.llm_helpers import refinePrompt
from .__PluginBase import PluginBase


def parse_arguments(prompt: str) -> tuple[str, Dict[str, Any]]:
    """
    Parse command-line style arguments from the prompt.

    Supports arguments like:
    - --aspect 16:9
    - --aspect square
    - --aspect portrait
    - --aspect landscape

    Args:
        prompt: The input prompt with potential arguments

    Returns:
        tuple: (cleaned_prompt, config_dict)
    """
    config: Dict[str, Any] = {}
    cleaned_prompt = prompt

    # Define supported arguments and their patterns
    # Pattern matches: --arg value or --arg=value
    arg_patterns = [
        (r"--aspect\s+(\S+)", "aspect"),
        (r"--aspect=(\S+)", "aspect"),
    ]

    for pattern, key in arg_patterns:
        matches = list(re.finditer(pattern, cleaned_prompt, re.IGNORECASE))
        if matches:
            # Take the last occurrence value if multiple are found
            config[key] = matches[-1].group(1)
            # Remove all occurrences from the prompt (in reverse order to preserve indices)
            for match in reversed(matches):
                cleaned_prompt = (
                    cleaned_prompt[: match.start()] + cleaned_prompt[match.end() :]
                )

    # Clean up extra whitespace
    cleaned_prompt = " ".join(cleaned_prompt.split())

    return cleaned_prompt.strip(), config


def img(
    prompt: str,
    media: list,
    backend: Ircawp_Backend,
    media_backend: MediaBackend = None,
) -> tuple[str, str, bool]:
    # Parse command-line style arguments from the prompt
    cleaned_prompt, config = parse_arguments(prompt)

    # Log parsed configuration if any arguments were found
    if config:
        backend.console.log(f"[cyan]Parsed arguments: {config}")
        backend.console.log(f"[cyan]Cleaned prompt: '{cleaned_prompt}'")

    # we don't run the imagegen here, we just pass it all back
    # to ircawp to process without inference

    if cleaned_prompt and cleaned_prompt[0] == "!":
        refined_prompt = cleaned_prompt[1:]
        backend.console.log("[white on green] skipping prompt refinement")
    else:
        refined_prompt = refinePrompt(cleaned_prompt, backend, media)

    # Clean up the refined prompt
    final_prompt = refined_prompt.strip()

    if "i'm sorry" in final_prompt.lower() or "i cannot" in final_prompt.lower():
        backend.console.log("[pink on red] prompt refinement refused, using original")
        final_prompt = cleaned_prompt.strip()

    backend.console.log(f"[black on green] refined prompt: '{final_prompt}'")

    # Call media backend to generate the image
    image_path = media_backend.execute(prompt=final_prompt, config=config)

    # return "Refined prompt:\n```" + final_prompt.strip() + "```", image_path, False
    return "", image_path, False, {"imagegen_prompt": final_prompt}


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

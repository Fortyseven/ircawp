"""
Bot plugin that allows the user to pass a raw prompt to the system imagegen backend and post a response.
"""

from typing import Dict, Any
from PIL import Image
from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend
from app.lib.args import parse_arguments as generic_parse_arguments, help_arguments
from .__PluginBase import PluginBase


def get_media_aspect_ratio(media_path: str) -> float:
    """Extract aspect ratio (width/height) from an image file."""
    try:
        img = Image.open(media_path)
        return img.width / img.height
    except Exception:
        return None


ARG_SPECS = {
    "aspect": {
        "names": ["--aspect"],
        "description": "Set aspect ratio (e.g. 16:9, or decimal 1.78) or 'match' to use input media aspect",
        "type": str,
    },
    "batch": {
        "names": ["--batch"],
        "description": "Generate multiple images and combine into a grid (max 4)",
        "type": int,
    },
    "scale": {
        "names": ["--scale"],
        "description": "Set the scale factor for image generation",
        "type": float,
    },
    "remaster": {
        "names": ["--remaster"],
        "description": "Enable remastering of the generated image (uses a custom prompt to enhance details)",
        "type": bool,
    },
    "andthen": {
        "names": ["--andthen", "--andnow", "--then", "--next", "--now", "--edit"],
        "description": "Chain another image edit after this one",
        "type": bool,
    },
    # "undo": {
    #     "names": ["--undo", "--oops", "--actuallyno", "--no"],
    #     "description": "Revert to the previous generated image and perform a new generation using it as input",
    #     "type": bool,
    # },
    "redo": {
        "names": ["--redo", "--tryagain", "--again"],
        "description": "Re-run the last generation exactly (cannot be combined with prompts, media, or other flags)",
        "type": bool,
    },
    "again": {
        # this is like prompting "add a ball" and then doing it again, adding a second ball to the resulting image
        "names": ["--again"],
        "description": "Perform the prompt again on the most recently generated image (same as --andthen with the same refined prompt)",
        "type": bool,
    },
    "remix": {
        "names": ["--remix"],
        "description": "Generate a remix of the input image",
        "type": bool,
    },
    "wordle": {
        "names": ["--wordle"],
        "description": "Solve a Wordle puzzle from an image of the game board",
        "type": bool,
    },
    "help": {
        "names": ["--help", "-h"],
        "description": "Show this help message",
        "type": bool,
    },
}


def _parse_arguments(prompt: str) -> tuple[str, Dict[str, Any]]:
    return generic_parse_arguments(prompt, ARG_SPECS)


def _has_invalid_argument(prompt: str) -> bool:
    import re

    matches = re.findall(r"--\w+", prompt)
    valid_args = {name for spec in ARG_SPECS.values() for name in spec["names"]}
    for match in matches:
        if match not in valid_args:
            return True
    return False


def img(
    prompt: str,
    media: list,
    backend: Ircawp_Backend,
    media_backend: MediaBackend = None,
) -> tuple[str, str, bool]:
    from ._img_utils.batch import doBatchImages
    from ._img_utils.single import (
        doSingleImage,
        getLastRefinedPrompt,
        getLastGeneratedMedia,
    )
    from ._img_utils.remix import subcommand_remix
    from ._img_utils.wordle import subcommand_wordle
    from ._img_utils.redo import submodule_redo

    if not media and not prompt:
        return (
            "A prompt or image must be provided. Use `/img --help` for usage information.",
            "",
            False,
            {},
        )

    if _has_invalid_argument(prompt):
        backend.console.log(
            "[yellow on black] Detected command-line style arguments in prompt"
        )
        return help_arguments(ARG_SPECS), "", False, {}

    # Parse command-line style arguments from the prompt
    prompt, config = _parse_arguments(prompt)

    # Validate --remaster requires media
    if config.get("remaster", False) and not media:
        return (
            "The --remaster flag requires a media attachment (input image).",
            "",
            False,
            {},
        )

    # Handle --redo FIRST: validate and restore previous generation state
    if config.get("remix", False):
        return subcommand_remix(prompt, media, backend, media_backend)

    if config.get("again", False):
        if getLastRefinedPrompt() is None:
            return (
                "No previous refined prompt to use for --again. Run `/img` first.",
                "",
                False,
                {},
            )
        # Use the last refined prompt with the most recent media
        prompt = getLastRefinedPrompt()
        media = getLastGeneratedMedia()
        backend.console.log("[cyan on black] reusing last refined prompt for --again")

    if config.get("redo", False):
        return submodule_redo(prompt, media, backend, media_backend, config)

    if config.get("help", False):
        return help_arguments(ARG_SPECS), "", False, {}

    if config.get("wordle", False):
        return subcommand_wordle(prompt, media, backend, media_backend)

    # remaster is passed as a config flag to the media
    # backend, which can choose to use it or not

    # Handle --undo: use previous image if available (takes precedence over --andthen)
    # if config.get("undo", False) and config.get("batch", 1) == 1:
    #     if getUndoMedia():
    #         # # If no prompt, just restore the previous image without generating
    #         # if not prompt or prompt.strip() == "":
    #         #     shutil.copy(UNDO_IMAGE_PATH, LAST_GENERATED_IMAGE_PATH)
    #         #     backend.console.log("[cyan on black] restored previous image (undo)")
    #         #     return "", UNDO_IMAGE_PATH, False, {}

    #         # Otherwise use previous image as input for new generation
    #         media = getUndoMedia()
    #         backend.console.log("[cyan on black] using previous image for undo")

    if config.get("andthen", False):
        # check if we have a saved copy of the prior media run, use that as
        # our media input

        # remove LAST_IMAGE_PATH
        if not getLastGeneratedMedia():
            return (
                "No previous generation to use for --andthen. Run `/img` first.",
                "",
                False,
                {},
            )
        media = getLastGeneratedMedia()
        backend.console.log(
            "[cyan on black] chaining from last generation for --andthen"
        )

    # Handle --aspect match: if media is provided and aspect is match (or not specified),
    # automatically set aspect to the media's aspect ratio
    if media:
        aspect_value = config.get("aspect")
        if aspect_value == "match" or aspect_value is None:
            media_aspect = get_media_aspect_ratio(media[0])
            if media_aspect is not None:
                config["aspect"] = media_aspect
                if aspect_value is None:
                    backend.console.log(
                        f"[cyan on black] defaulting to media aspect ratio: {media_aspect:.2f}"
                    )
                else:
                    backend.console.log(
                        f"[cyan on black] matched media aspect ratio: {media_aspect:.2f}"
                    )

    if prompt.startswith("!"):
        backend.console.log("[white on green] skipping prompt refinement")
        config["skip_refinement"] = True
        prompt = prompt[1:]

    # final_prompt = ""

    # Clean up the refined prompt
    if config.get("batch", 1) > 4:
        config["batch"] = 4

    if config.get("batch", 1) > 1:
        return doBatchImages(prompt, media, backend, media_backend, config)

    return doSingleImage(prompt, media, backend, media_backend, config)

    # return "Refined prompt:\n```" + final_prompt.strip() + "```", image_path, False


plugin = PluginBase(
    name="Image Generator",
    description="Pass a raw prompt to the image generator.",
    triggers=["img"],
    system_prompt="",
    emoji_prefix="",
    msg_empty_query="No prompt provided",
    prompt_required=False,
    msg_exception_prefix="ARTISTIC PROBLEMS",
    main=img,
    use_imagegen=False,
)

"""
Bot plugin that allows the user to pass a raw prompt to the system imagegen backend and post a response.
"""

import shutil
import glob
from typing import Dict, Any
from pathlib import Path
from PIL import Image
from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend
from app.lib.args import parse_arguments as generic_parse_arguments
from .__PluginBase import PluginBase

LAST_GENERATED_IMAGE_PATH = "/tmp/ircawp.last_imagegen_media.png"
UNDO_IMAGE_PATH = "/tmp/ircawp.previous_imagegen_media.png"
LAST_UPLOADED_MEDIA_PREFIX = "/tmp/ircawp.uploaded_media"
REDO_MEDIA_PATH_PREFIX = "/tmp/ircawp.redo_media"

# Module-level state for --redo functionality
last_redo_prompt: str = None
last_refined_prompt: str = None
last_redo_media: list = None
last_redo_config: dict = None


def get_media_aspect_ratio(media_path: str) -> float:
    """Extract aspect ratio (width/height) from an image file."""
    try:
        img = Image.open(media_path)
        return img.width / img.height
    except Exception:
        return None


def _cleanup_redo_media() -> None:
    """Remove old redo media files to prevent accumulation."""
    try:
        for old_file in glob.glob(f"{REDO_MEDIA_PATH_PREFIX}_*"):
            Path(old_file).unlink(missing_ok=True)
    except Exception:
        pass  # Silently ignore cleanup errors


def _save_redo_media(media: list) -> list:
    """Save media files to persistent temp paths for --redo functionality.

    Args:
        media: List of media file paths (will be deleted after plugin execution)

    Returns:
        List of persistent paths in /tmp/ircawp.redo_media_* format
    """
    if not media:
        return []

    # Clean up old redo media files first
    _cleanup_redo_media()

    persistent_paths = []
    for i, media_path in enumerate(media):
        try:
            # Get file extension from original path
            ext = Path(media_path).suffix or ".png"
            persistent_path = f"{REDO_MEDIA_PATH_PREFIX}_{i}{ext}"

            # Copy to persistent location
            shutil.copy(media_path, persistent_path)
            persistent_paths.append(persistent_path)
        except Exception:
            # If we fail to save any media, bail out
            return []

    return persistent_paths


def _doBatchImages(prompt, media, backend, media_backend, config):
    image_paths = []
    for i in range(config["batch"]):
        # Call media backend to generate the image
        image_path, final_prompt = media_backend.execute(
            prompt=prompt, config=config, batch_id=i, media=media, backend=backend
        )
        image_paths.append(image_path)

    # combine them into one image grid
    try:
        # Use up to 4 images in a 2x2 grid
        imgs = image_paths[:4]
        opened = [Image.open(p).convert("RGB") for p in imgs]

        # Normalize sizes: resize all to the size of the smallest (by area)
        areas = [im.width * im.height for im in opened]
        min_idx = areas.index(min(areas))
        base_w, base_h = opened[min_idx].width, opened[min_idx].height
        resized = [im.resize((base_w, base_h)) for im in opened]

        # Create grid canvas 2x2 (fill missing with black if <4)
        grid_w, grid_h = base_w * 2, base_h * 2
        canvas = Image.new("RGB", (grid_w, grid_h), color=(0, 0, 0))

        positions = [(0, 0), (base_w, 0), (0, base_h), (base_w, base_h)]
        for i, im in enumerate(resized):
            canvas.paste(im, positions[i])

        # Save grid next to first image
        first_path = Path(imgs[0])
        grid_name = first_path.stem + "_grid.jpg"
        grid_path = str(first_path.with_name(grid_name))
        canvas.save(grid_path, format="JPEG", quality=92)

        # Return the grid image
        return "", grid_path, False, {}
    except Exception as e:
        backend.console.log(f"[pink on red] grid compose failed: {e}")
        # fall through to single image return


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
        "names": ["--andthen", "--then", "--next", "--now", "--edit"],
        "description": "Chain another image edit after this one",
        "type": bool,
    },
    "undo": {
        "names": ["--undo", "--oops", "--actuallyno", "--no"],
        "description": "Revert to the previous generated image and perform a new generation using it as input",
        "type": bool,
    },
    "redo": {
        "names": ["--redo", "--tryagain", "--again"],
        "description": "Re-run the last generation exactly (cannot be combined with prompts, media, or other flags)",
        "type": bool,
    },
    "again": {
        "names": ["--again"],
        "description": "Perform the prompt again on the most recently generated image (same as --andthen with the same refined prompt)",
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


def subcommand_wordle(
    prompt: str,
    media: list,
    backend: Ircawp_Backend,
    media_backend: MediaBackend = None,
) -> tuple[str, str, bool]:
    from pydantic import BaseModel

    class WordleWordsResponse(BaseModel):
        words: list[str] = []

    SPROMPT = """
You are an expert at solving Wordle puzzles. Given an image of a Wordle game board, extract the letters and their colors (green, yellow, gray) and provide the next best guess word based on the current state of the board.
"""
    # ensure one image is provided
    if not media or len(media) != 1:
        return (
            "Wordle subcommand requires exactly one input image.",
            "",
            False,
            {},
        )

    # run inference to extract letters from image

    response, _ = backend.runInference(
        system_prompt=SPROMPT,
        # prompt=text,
        media=media,
        use_tools=False,
        format=WordleWordsResponse,
        temperature=0.1,
    )

    print(response)

    words = WordleWordsResponse.model_validate_json(response)

    config = {"batch": 4, "aspect": "4:3"}

    batch = _doBatchImages(" ".join(words.words), [], backend, media_backend, config)

    # add extracted words to the response
    foo, bar, baz, quux = batch

    return (
        f"Extracted words: `{', '.join(words.words)}`",
        bar,
        baz,
        quux,
    )


def subcommand_help() -> tuple[str, str, bool]:
    help_text = "Available `/img` subcommands:\n"

    for arg, spec in ARG_SPECS.items():
        names = ", ".join(f"`{name}`" for name in spec["names"])
        description = spec["description"]
        help_text += f"{names}: {description}\n"

    return help_text.strip(), "", False, {}


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
    global last_redo_prompt, last_redo_media, last_redo_config, last_refined_prompt

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
        return subcommand_help()

    # Parse command-line style arguments from the prompt
    prompt, config = _parse_arguments(prompt)

    # Handle --redo FIRST: validate and restore previous generation state
    if config.get("again", False):
        if last_refined_prompt is None:
            return (
                "No previous refined prompt to use for --again. Run `/img` first.",
                "",
                False,
                {},
            )
        # Use the last refined prompt with the most recent media
        prompt = last_refined_prompt
        media = (
            [LAST_GENERATED_IMAGE_PATH]
            if Path(LAST_GENERATED_IMAGE_PATH).is_file()
            else []
        )
        backend.console.log("[cyan on black] reusing last refined prompt for --again")
    elif config.get("redo", False):
        # Validate: no new prompt provided (after flag parsing)
        if prompt and prompt.strip():
            return (
                "Cannot combine --redo with a new prompt. Use `/img --redo` alone.",
                "",
                False,
                {},
            )

        # Validate: no new media provided
        if media:
            return (
                "Cannot combine --redo with new media. Use `/img --redo` alone.",
                "",
                False,
                {},
            )

        # Validate: no other conflicting flags
        conflicting = [k for k in ["undo", "andthen", "wordle"] if config.get(k)]
        if conflicting:
            return (
                f"Cannot combine --redo with other flags: {', '.join(conflicting)}",
                "",
                False,
                {},
            )

        # Check if we have saved state
        if last_redo_prompt is None:
            return (
                "No previous generation to redo. Run `/img` first.",
                "",
                False,
                {},
            )

        # Verify saved media files still exist
        for media_path in last_redo_media or []:
            if not Path(media_path).is_file():
                return (
                    f"Redo media file missing: {media_path}",
                    "",
                    False,
                    {},
                )

        # Restore state (overwrites parsed values)
        prompt = last_redo_prompt
        media = last_redo_media if last_redo_media else []
        config = last_redo_config.copy()  # Copy to avoid mutation
        backend.console.log("[cyan on black] loaded redo state from memory")
    else:
        # Save state for future --redo (only if NOT currently doing a redo)
        last_redo_prompt = prompt
        last_redo_config = config.copy()  # Copy to avoid external mutations
        last_redo_media = _save_redo_media(media) if media else []

    if config.get("help", False):
        return subcommand_help()

    if config.get("wordle", False):
        return subcommand_wordle(prompt, media, backend, media_backend)

    # remaster is passed as a config flag to the media
    # backend, which can choose to use it or not

    # Handle --undo: use previous image if available (takes precedence over --andthen)
    if config.get("undo", False) and config.get("batch", 1) == 1:
        if Path(UNDO_IMAGE_PATH).is_file():
            # If no prompt, just restore the previous image without generating
            if not prompt or prompt.strip() == "":
                shutil.copy(UNDO_IMAGE_PATH, LAST_GENERATED_IMAGE_PATH)
                backend.console.log("[cyan on black] restored previous image (undo)")
                return "", UNDO_IMAGE_PATH, False, {}

            # Otherwise use previous image as input for new generation
            media = [UNDO_IMAGE_PATH]
            backend.console.log("[cyan on black] using previous image for undo")

    if config.get("andthen", False):
        # check if we have a saved copy of the prior media run, use that as
        # our media input

        # remove LAST_IMAGE_PATH
        if not Path(LAST_GENERATED_IMAGE_PATH).is_file():
            image_path, final_prompt = media_backend.execute(
                prompt="A red background, white text: 'Sorry, no last image found!'",
                backend=backend,
            )
            return "", image_path, False, {"imagegen_prompt": final_prompt}

        media = [LAST_GENERATED_IMAGE_PATH]

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

    final_prompt = ""

    # Clean up the refined prompt
    if config.get("batch", 1) > 4:
        config["batch"] = 4

    if config.get("batch", 1) > 1:
        return _doBatchImages(prompt, media, backend, media_backend, config)

    last_refined_prompt = prompt  # for --again

    # Call media backend to generate the image
    image_path, final_prompt = media_backend.execute(
        prompt=prompt, config=config, media=media, backend=backend
    )

    # if media and REDO_MEDIA_PATH not in media[0]:
    #     # save first media image to a temp file for reuse if asked
    #     shutil.copy(media[0], REDO_MEDIA_PATH)
    #     backend.console.log(
    #         f"[red on green] Saved REDO_MEDIA_PATH: {REDO_MEDIA_PATH!r}"
    #     )

    # Save current LAST_IMAGE_PATH to PREVIOUS_IMAGE_PATH before updating
    if Path(LAST_GENERATED_IMAGE_PATH).is_file():
        shutil.copy(LAST_GENERATED_IMAGE_PATH, UNDO_IMAGE_PATH)

    shutil.copy(image_path, LAST_GENERATED_IMAGE_PATH)

    # return "Refined prompt:\n```" + final_prompt.strip() + "```", image_path, False
    return "", image_path, False, {"imagegen_prompt": final_prompt}


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

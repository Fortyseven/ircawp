"""
Bot plugin that allows the user to pass a raw prompt to the system imagegen backend and post a response.
"""

import shutil
from typing import Dict, Any
from pathlib import Path
from PIL import Image
from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend
from app.lib.args import parse_arguments as generic_parse_arguments
from .__PluginBase import PluginBase

REDO_MEDIA_PATH = "/tmp/ircawp.last_imagegen_media.png"
last_unrefined_prompt: str = None


def get_media_aspect_ratio(media_path: str) -> float:
    """Extract aspect ratio (width/height) from an image file."""
    try:
        img = Image.open(media_path)
        return img.width / img.height
    except Exception:
        return None


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


def parse_arguments(prompt: str) -> tuple[str, Dict[str, Any]]:
    arg_specs = {
        "aspect": {
            "names": ["--aspect"],
            "type": str,
        },
        "batch": {
            "names": ["--batch"],
            "type": int,
        },
    }

    return generic_parse_arguments(prompt, arg_specs)


def img(
    prompt: str,
    media: list,
    backend: Ircawp_Backend,
    media_backend: MediaBackend = None,
) -> tuple[str, str, bool]:
    global last_unrefined_prompt

    # Parse command-line style arguments from the prompt
    prompt, config = parse_arguments(prompt)

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
    else:
        # remove REDO_MEDIA_PATH
        if Path(REDO_MEDIA_PATH).is_file():
            Path(REDO_MEDIA_PATH).unlink()

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

    # Call media backend to generate the image
    image_path, final_prompt = media_backend.execute(
        prompt=prompt, config=config, media=media, backend=backend
    )

    if media and REDO_MEDIA_PATH not in media[0]:
        # save first media image to a temp file for reuse if asked
        shutil.copy(media[0], REDO_MEDIA_PATH)
        backend.console.log(
            f"[red on green] Saved REDO_MEDIA_PATH: {REDO_MEDIA_PATH!r}"
        )

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

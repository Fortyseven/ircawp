"""
Bot plugin that allows the user to pass a raw prompt to the system imagegen backend and post a response.
"""

import shutil
from typing import Dict, Any
from pathlib import Path
from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend
from app.lib.llm_helpers import refinePrompt
from app.lib.args import parse_arguments as generic_parse_arguments
from .__PluginBase import PluginBase

REDO_MEDIA_PATH = "/tmp/ircawp.last_imagegen_media.png"
last_unrefined_prompt: str = None


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

    if prompt.startswith("!!"):
        # redo prior session run
        backend.console.log("[red on green] reusing last unrefined prompt or media")

        # if prior run had a supplied image, reuse it
        have_reuse_media = Path(REDO_MEDIA_PATH).is_file()
        backend.console.log(f"[red on green] have_reuse_media: {have_reuse_media}")
        last_media = REDO_MEDIA_PATH if have_reuse_media else ""

        backend.console.log(f"[red on green] MEDIA: {last_media!r}")

        # prompt = last_unrefined_prompt or prompt[2:]

        refined_prompt = refinePrompt(prompt[2:].strip(), backend, [last_media])
        last_unrefined_prompt = prompt[2:]

    elif prompt.startswith("!"):
        backend.console.log("[white on green] skipping prompt refinement")
        refined_prompt = prompt[1:]
        last_unrefined_prompt = prompt[1:]
    else:
        last_unrefined_prompt = prompt
        refined_prompt = refinePrompt(prompt.strip(), backend, media)

    # Clean up the refined prompt
    final_prompt = refined_prompt.strip()

    if "i'm sorry" in final_prompt.lower() or "i cannot" in final_prompt.lower():
        backend.console.log("[pink on red] prompt refinement refused, using original")
        final_prompt = prompt.strip()

    backend.console.log(f"[black on green] refined prompt: '{final_prompt}'")

    if config.get("batch", 1) > 4:
        config["batch"] = 4

    if config.get("batch", 1) > 1:
        image_paths = []
        for i in range(config["batch"]):
            # Call media backend to generate the image
            image_path = media_backend.execute(
                prompt=final_prompt, config=config, batch_id=i
            )
            image_paths.append(image_path)

        # combine them into one image grid
        try:
            from PIL import Image

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

    # Call media backend to generate the image
    image_path = media_backend.execute(prompt=final_prompt, config=config)

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

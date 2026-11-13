from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend
from app.lib.llm_helpers import refinePrompt
from PIL import Image
from pathlib import Path


def _layout_for_count(
    n: int, base_w: int, base_h: int
) -> tuple[int, int, list[tuple[int, int]]]:
    """Compute canvas size and paste positions for n images of base_w x base_h.

    4 images keep the classic 2x2 grid. Otherwise images are stacked along
    their longer edge: landscape (w >= h) in a vertical column, portrait in a
    horizontal row, so the composite never has empty cells.
    """
    if n == 4:
        return (
            base_w * 2,
            base_h * 2,
            [(0, 0), (base_w, 0), (0, base_h), (base_w, base_h)],
        )
    if base_w >= base_h:
        # landscape: stack vertically along the long (horizontal) edge
        return base_w, base_h * n, [(0, base_h * i) for i in range(n)]
    # portrait: stack horizontally along the long (vertical) edge
    return base_w * n, base_h, [(base_w * i, 0) for i in range(n)]


def _compose_grid(image_paths: list[str], backend) -> str:
    """Stitch batch images into one composite saved next to the first image.

    All images are resized to the smallest one's dimensions (by area), then
    laid out per _layout_for_count. Returns the composite path, or "" on
    failure so the caller can fall back to the first generated image.
    """
    try:
        imgs = image_paths[:4]
        opened = [Image.open(p).convert("RGB") for p in imgs]

        # Normalize sizes: resize all to the size of the smallest (by area)
        areas = [im.width * im.height for im in opened]
        min_idx = areas.index(min(areas))
        base_w, base_h = opened[min_idx].width, opened[min_idx].height
        resized = [im.resize((base_w, base_h)) for im in opened]

        canvas_w, canvas_h, positions = _layout_for_count(len(resized), base_w, base_h)
        canvas = Image.new("RGB", (canvas_w, canvas_h), color=(0, 0, 0))
        for im, pos in zip(resized, positions):
            canvas.paste(im, pos)

        # Save grid next to first image
        first_path = Path(imgs[0])
        grid_name = first_path.stem + "_grid.jpg"
        grid_path = first_path.with_name(grid_name)
        canvas.save(str(grid_path), format="JPEG", quality=92)
        return str(grid_path)
    except Exception as e:
        backend.console.log(f"[pink on red] grid compose failed: {e}")
        return ""


def doBatchImages(
    prompt,
    media,
    backend,
    media_backend,
    config,
    skip_refinement: bool = False,
):
    # Guard: no image generation backend configured (mirrors doSingleImage).
    if media_backend is None:
        backend.console.log(
            "[red] /img --batch requested but no image generation backend is configured (None)"
        )
        return (
            "Image generation is not available — no image generator backend is configured on this instance (was None).",
            "",
            False,
            {},
        )
    else:
        backend.console.log(
            f"[green] /img --batch using image generation backend: {media_backend.backend_id}"
        )

    image_paths = []
    is_edit = len(media) > 0

    for i in range(config["batch"]):
        # Refine prompt independently for each image in the batch
        if not skip_refinement:
            refined_prompt = refinePrompt(prompt, backend, media, is_edit=is_edit)
            batch_prompt = refined_prompt.strip()
            if (
                "i'm sorry" in batch_prompt.lower()
                or "i cannot" in batch_prompt.lower()
            ):
                backend.console.log(
                    f"[pink on red] batch image {i + 1}: refinement refused, using original"
                )
                batch_prompt = prompt.strip()
            else:
                backend.console.log(
                    f"[black on green] batch image {i + 1} refined prompt: '{batch_prompt}'"
                )
        else:
            batch_prompt = prompt.strip()

        # Call media backend to generate the image
        image_path, final_prompt = media_backend.execute(
            prompt=batch_prompt,
            config=config,
            batch_id=i,
            media=media,
            backend=backend,
        )
        image_paths.append(image_path)

    # combine them into one image grid; fall back to the first image
    grid_path = _compose_grid(image_paths, backend)
    if grid_path:
        return "", grid_path, False, {}

    first_image = image_paths[0] if image_paths and image_paths[0] else ""
    return "", first_image, False, {}

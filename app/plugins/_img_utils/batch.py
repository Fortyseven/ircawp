from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend
from PIL import Image


def doBatchImages(prompt, media, backend, media_backend, config):
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

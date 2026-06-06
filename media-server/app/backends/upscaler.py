"""Image upscaling utility for media-server."""

from super_image import EdsrModel, ImageLoader
from PIL import Image
import torch


def upscale_image(input_path: str, scale: int = 2) -> str:
    """Upscale an image using the EDSR model."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.cuda.empty_cache()

    model = EdsrModel.from_pretrained("eugenesiow/edsr-base", scale=scale).to(device)
    model.eval()

    inputs = ImageLoader.load_image(input_path).to(device)
    preds = model(inputs)

    output_path = "/tmp/ircawp_generated/scaled.png"
    ImageLoader.save_image(preds, output_path)

    return output_path

from super_image import EdsrModel, ImageLoader
from PIL import Image
import torch


def upscaleImage(input_path: str, scale: int = 2) -> str:
    """
    Upscales an image using the EDSR model from the super_image library.

    Args:
        input_path (str): Path to the input image file.
        output_path (str): Path where the upscaled image will be saved.
        scale_factor (int): The factor by which to upscale the image. Default is 4.

    Returns:
        str: Path to the saved upscaled image.
    """

    device = "cuda" if torch.cuda.is_available() else "cpu"

    torch.cuda.empty_cache()
    # Load the pre-trained EDSR model
    model = EdsrModel.from_pretrained("eugenesiow/edsr-base", scale=scale).to(device)
    model.eval()

    inputs = ImageLoader.load_image(input_path).to(device)

    preds = model(inputs)
    # preds = preds.data.cpu().numpy()

    output_path = "/tmp/ircawp.scaled.png"
    ImageLoader.save_image(preds, output_path)

    return output_path

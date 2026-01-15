from app.backends.Ircawp_Backend import Ircawp_Backend
from PIL import Image, PngImagePlugin


class MediaBackend:
    def __init__(self, backend: Ircawp_Backend = None):
        self.backend = backend
        self.last_imagegen_prompt = None

    def execute(
        self, prompt: str, config: dict = {}, batch_id=None, media=[], backend=None
    ) -> str:
        return ""

    def _save_image_with_metadata(
        self, image: Image.Image, output_path: str, prompt: str, **metadata_kwargs
    ) -> None:
        """Save PIL Image to PNG with embedded text metadata.

        Args:
            image: PIL Image object to save
            output_path: Path to save PNG file
            prompt: The final prompt used during generation
            **metadata_kwargs: Additional metadata key-value pairs (e.g., seed, model, guidance_scale)
        """
        pnginfo = PngImagePlugin.PngInfo()

        # Always include the prompt
        pnginfo.add_text("prompt", str(prompt))

        # Add any additional metadata
        for key, value in metadata_kwargs.items():
            if value is not None:
                pnginfo.add_text(key, str(value))

        image.save(output_path, pnginfo=pnginfo)

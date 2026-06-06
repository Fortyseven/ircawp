"""Base class for media (image generation) backends.

This is the media-server side — strictly prompt-in → image-out.
No LLM calls, no prompt refinement.
"""

from PIL import Image, PngImagePlugin


class MediaBackend:
    def __init__(self):
        self.last_imagegen_prompt = None

    def execute(
        self, prompt: str, config: dict = {}, batch_id=None, media=[]
    ) -> str | tuple[str, str]:
        """Execute image generation.

        Returns:
            str: path to generated image, or
            tuple[str, str]: (path, final_prompt)
        """
        return ""

    def _save_image_with_metadata(
        self,
        image: Image.Image,
        output_path: str,
        prompt: str,
        **metadata_kwargs,
    ) -> None:
        """Save PIL Image to PNG with embedded text metadata."""
        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add_text("prompt", str(prompt))
        for key, value in metadata_kwargs.items():
            if value is not None:
                pnginfo.add_text(key, str(value))
        image.save(output_path, pnginfo=pnginfo)

"""Base class for media (image generation) backends.

This is the media-server side — strictly prompt-in → image-out.
No LLM calls, no prompt refinement.
"""

from PIL import Image, PngImagePlugin


class GenerationCancelled(Exception):
    """Raised when a generation backend observes a cancellation request."""


class MediaBackend:
    def __init__(self, backend_config: dict = {}):
        self.backend_config = backend_config
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

    @staticmethod
    def raise_if_cancelled(config: dict) -> None:
        """Abort cooperative backend work when the request has been cancelled."""
        cancellation_event = config.get("cancellation_event")
        if cancellation_event is not None and cancellation_event.is_set():
            raise GenerationCancelled()

    def cancellation_callback(self, config: dict, total_steps: int | None = None):
        """Return a diffusers-compatible callback that observes cancellation and reports progress."""
        progress_state = config.get("progress_state")

        def callback(pipe, step_index, timestep, callback_kwargs):
            self.raise_if_cancelled(config)
            if progress_state is not None:
                progress_state["step"] = step_index + 1
                if total_steps is not None:
                    progress_state["total_steps"] = total_steps
            return callback_kwargs

        return callback


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

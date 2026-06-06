"""HTTP client for the ircawp media-server.

Replaces direct backend instantiation with HTTP calls to the media-server.
Maintains the same execute() signature so all plugin call-sites remain unchanged.

Uses the OpenAI-compatible JSON API (POST /images/generations, POST /images/edits).
"""

import base64
import json
import tempfile
from pathlib import Path

import requests


class MediaBackend:
    """HTTP client wrapper for the media-server image generation API."""

    def __init__(self, server_url: str, backend_id: str = "flux2klein"):
        """
        Args:
            server_url: Base URL of the media-server (e.g. "http://localhost:8100")
            backend_id: Default backend to use (e.g. "flux2klein")
        """
        self.server_url = server_url.rstrip("/")
        self.backend_id = backend_id
        self.last_imagegen_prompt = None

    def execute(
        self,
        prompt: str,
        config: dict = {},
        batch_id=None,
        media=[],
        backend=None,
    ) -> tuple[str, str]:
        """Execute image generation via the media-server.

        Args:
            prompt: Final prompt (refinement should already be done by caller)
            config: Generation config (aspect, scale, remaster, etc.)
            batch_id: Optional batch index for multi-image generation
            media: List of local file paths to input images
            backend: Ircawp_Backend (kept for signature compatibility, not used)

        Returns:
            tuple[str, str]: (local_image_path, final_prompt)
        """
        has_media = len(media) > 0

        # Build JSON body
        body = {
            "prompt": prompt,
            "model": self.backend_id,
        }

        # Map config to OpenAI-style params
        if "width" in config and "height" in config:
            body["size"] = f"{config['width']}x{config['height']}"
        elif "aspect" in config:
            # Convert aspect ratio to a size string if max_output_size is provided
            max_size = config.get("max_output_size", 1024)
            aspect = config["aspect"]
            if isinstance(aspect, str) and ":" in aspect:
                parts = aspect.split(":")
                if len(parts) == 2:
                    try:
                        aspect = float(parts[0]) / float(parts[1])
                    except ValueError:
                        aspect = 1.5
            elif isinstance(aspect, (int, float)):
                pass
            else:
                try:
                    aspect = float(aspect)
                except (ValueError, TypeError):
                    aspect = 1.5

            if aspect >= 1.0:
                w, h = max_size, int(max_size / aspect)
            else:
                w, h = int(max_size * aspect), max_size
            body["size"] = f"{w}x{h}"

        if config.get("remaster"):
            body["quality"] = "high"

        # If there are input media, use /images/edits
        if has_media:
            url = f"{self.server_url}/images/edits"

            # Encode media as base64 data URLs
            images = []
            for media_path in media:
                path = Path(media_path)
                if path.is_file():
                    with open(path, "rb") as f:
                        image_bytes = f.read()
                    image_b64 = base64.b64encode(image_bytes).decode("ascii")
                    ext = path.suffix.lower()
                    mime_map = {
                        ".png": "image/png",
                        ".jpg": "image/jpeg",
                        ".jpeg": "image/jpeg",
                        ".webp": "image/webp",
                    }
                    mime = mime_map.get(ext, "image/png")
                    images.append({"image_url": f"data:{mime};base64,{image_b64}"})

            body["images"] = images
        else:
            url = f"{self.server_url}/images/generations"

        try:
            response = requests.post(url, json=body)
            response.raise_for_status()
            result = response.json()

            # Extract the first image from the response
            data = result.get("data", [])
            if not data:
                raise ValueError("No image data in response")

            image_b64 = data[0].get("b64_json", "")
            image_bytes = base64.b64decode(image_b64)

            # Determine extension from content (default to png)
            ext = ".png"

            # Write to temp file
            if batch_id is not None:
                local_path = tempfile.NamedTemporaryFile(
                    suffix=f".{batch_id}{ext}", delete=False, dir="/tmp"
                ).name
            else:
                local_path = tempfile.NamedTemporaryFile(
                    suffix=ext, delete=False, dir="/tmp"
                ).name

            with open(local_path, "wb") as f:
                f.write(image_bytes)

            # Get final prompt from revised_prompt if available
            final_prompt = data[0].get("revised_prompt", prompt)
            self.last_imagegen_prompt = final_prompt

            return local_path, final_prompt

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Media server request failed: {e}") from e

"""HTTP client for the ircawp media-server.

Replaces direct backend instantiation with HTTP calls to the media-server.
Maintains the same execute() signature so all plugin call-sites remain unchanged.
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
        url = f"{self.server_url}/generate"

        # Build form data
        data = {
            "prompt": prompt,
            "backend_id": self.backend_id,
            "config_json": json.dumps(config),
        }

        # Upload media files
        files = []
        if media:
            for i, media_path in enumerate(media):
                path = Path(media_path)
                if path.is_file():
                    files.append(
                        (
                            "media",
                            (path.name, open(path, "rb"), "application/octet-stream"),
                        )
                    )

        try:
            response = requests.post(url, data=data, files=files if files else None)
            response.raise_for_status()
            result = response.json()

            # Decode base64 image data and write to local temp file
            image_b64 = result["image_data"]
            image_bytes = base64.b64decode(image_b64)

            # Determine extension from mime type
            mime_type = result.get("mime_type", "image/png")
            ext = ".png"
            if "jpeg" in mime_type:
                ext = ".jpg"
            elif "webp" in mime_type:
                ext = ".webp"

            # Write to temp file with a name matching the backend
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

            final_prompt = result.get("final_prompt", prompt)
            self.last_imagegen_prompt = final_prompt

            return local_path, final_prompt

        finally:
            # Close any opened file handles
            for item in files:
                if hasattr(item[1][1], "close"):
                    item[1][1].close()

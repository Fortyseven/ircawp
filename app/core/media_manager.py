"""Media file lifecycle management."""

import os
from pathlib import Path
from typing import List
from rich.console import Console


class MediaManager:
    """Manages media file lifecycle: validation, tracking, and cleanup."""

    def __init__(self, console: Console, media_dir: str = "/tmp/ircawp_media"):
        """
        Initialize the media manager.

        Args:
            console: Rich console for logging
            media_dir: Directory for temporary media files
        """
        self.console = console
        self.media_dir = media_dir

        # Ensure media directory exists
        Path(self.media_dir).mkdir(parents=True, exist_ok=True)

    def cleanup_media_files(self, media_paths: List[str]) -> None:
        """
        Delete media files that are no longer needed.

        Args:
            media_paths: List of media file paths to delete
        """
        for img_path in media_paths:
            if not img_path:
                continue

            try:
                p = Path(img_path)
                if p.is_file():
                    p.unlink()
                    self.console.log(
                        f"[blue on white]Deleted temp media file: {img_path}"
                    )
            except Exception as e:
                self.console.log(
                    f"[red on white]Failed to delete temp media file '{img_path}': {e}"
                )

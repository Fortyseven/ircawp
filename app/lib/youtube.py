"""YouTube audio download utilities using yt-dlp.

Provides functions to download audio from YouTube videos and extract metadata.
"""

import re
from pathlib import Path
from typing import Optional, Tuple, Dict
import yt_dlp


def extractVideoId(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL.

    Args:
        url: YouTube URL

    Returns:
        Video ID string, or None if not found
    """
    patterns = [
        r"(?:youtube\.com/watch\?v=)([\w-]+)",
        r"(?:youtube\.com/shorts/)([\w-]+)",
        r"(?:youtu\.be/)([\w-]+)",
        r"(?:youtube\.com/embed/)([\w-]+)",
        r"(?:youtube\.com/v/)([\w-]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def validateYouTubeUrl(url: str) -> bool:
    """Validate if a URL is a valid YouTube URL.

    Args:
        url: URL string to validate

    Returns:
        True if valid YouTube URL, False otherwise
    """
    # Support various YouTube URL formats
    patterns = [
        r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+",
        r"(?:https?://)?(?:www\.)?youtube\.com/shorts/[\w-]+",
        r"(?:https?://)?youtu\.be/[\w-]+",
        r"(?:https?://)?(?:www\.)?youtube\.com/embed/[\w-]+",
        r"(?:https?://)?(?:www\.)?youtube\.com/v/[\w-]+",
    ]

    for pattern in patterns:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    return False


def formatMetadata(metadata: Dict) -> str:
    """Format YouTube video metadata for user-friendly display.

    Args:
        metadata: Dictionary of video metadata from yt-dlp

    Returns:
        Formatted string with key video information
    """
    lines = []

    if title := metadata.get("title"):
        lines.append(f"**Title:** {title}")

    if channel := metadata.get("channel") or metadata.get("uploader"):
        lines.append(f"**Channel:** {channel}")

    if duration := metadata.get("duration"):
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        lines.append(f"**Duration:** {minutes}m {seconds}s")

    if upload_date := metadata.get("upload_date"):
        # Format from YYYYMMDD to readable format
        if len(upload_date) == 8:
            formatted_date = f"{upload_date[0:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
            lines.append(f"**Uploaded:** {formatted_date}")

    if view_count := metadata.get("view_count"):
        lines.append(f"**Views:** {view_count:,}")

    return "\n".join(lines)


def getYouTubeAudio(
    url: str,
    output_dir: str,
    max_duration: Optional[int] = None,
    max_size_mb: Optional[float] = None,
) -> Tuple[str, Dict]:
    """Download audio from YouTube video as MP3.

    Args:
        url: YouTube video URL
        output_dir: Directory to save audio file
        max_duration: Maximum video duration in seconds (None = unlimited)
        max_size_mb: Maximum file size in MB (None = unlimited)

    Returns:
        Tuple of (audio_file_path, metadata_dict)
        - audio_file_path: Full path to downloaded MP3 file
        - metadata_dict: Video metadata including title, duration, channel, etc.

    Raises:
        ValueError: If URL is invalid or video exceeds limits
        RuntimeError: If download fails
        FileNotFoundError: If yt-dlp cannot access the video
    """
    # Validate URL
    if not validateYouTubeUrl(url):
        raise ValueError(f"Invalid YouTube URL: {url}")

    # Ensure output directory exists
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Configure yt-dlp options
    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "outtmpl": str(output_path / "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
    }

    try:
        # First, extract info to check limits before downloading
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
            info = ydl.extract_info(url, download=False)

            if info is None:
                raise RuntimeError("Failed to extract video information")

            # Check duration limit
            duration = info.get("duration", 0)
            if max_duration is not None and duration > max_duration:
                minutes = int(duration // 60)
                max_minutes = int(max_duration // 60)
                raise ValueError(
                    f"Video duration ({minutes}m) exceeds limit ({max_minutes}m)"
                )

            # Check file size limit (approximate, based on filesize or filesize_approx)
            filesize = info.get("filesize") or info.get("filesize_approx", 0)
            if max_size_mb is not None and filesize > 0:
                size_mb = filesize / (1024 * 1024)
                if size_mb > max_size_mb:
                    raise ValueError(
                        f"Video file size (~{size_mb:.1f}MB) exceeds limit ({max_size_mb}MB)"
                    )

        # Download audio
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)

            if info_dict is None:
                raise RuntimeError("Download failed - no information returned")

            # Get the output filename
            video_id = info_dict.get("id", "unknown")
            audio_file = output_path / f"{video_id}.mp3"

            # Verify file was created
            if not audio_file.exists():
                raise RuntimeError(f"Audio file was not created: {audio_file}")

            # Extract relevant metadata
            metadata = {
                "title": info_dict.get("title", "Unknown"),
                "channel": info_dict.get("channel")
                or info_dict.get("uploader", "Unknown"),
                "duration": info_dict.get("duration", 0),
                "upload_date": info_dict.get("upload_date", ""),
                "view_count": info_dict.get("view_count", 0),
                "id": video_id,
                "url": url,
            }

            return str(audio_file), metadata

    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if "Private video" in error_msg or "not available" in error_msg:
            raise FileNotFoundError(f"Video not accessible: {error_msg}")
        raise RuntimeError(f"Download failed: {error_msg}") from e

    except Exception as e:
        # Catch-all for other errors
        if isinstance(e, (ValueError, FileNotFoundError, RuntimeError)):
            raise
        raise RuntimeError(f"Unexpected error downloading video: {e}") from e

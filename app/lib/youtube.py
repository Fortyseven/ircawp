"""Video audio download utilities using yt-dlp.

Provides functions to download audio from YouTube, Vimeo, and other video sites
that yt-dlp supports, and extract metadata.
"""

import re
import json
import hashlib
from pathlib import Path
from typing import Optional, Tuple, Dict
import yt_dlp
import requests


def extractVideoId(url: str) -> str:
    """Extract video ID from URL using yt-dlp.

    Attempts to extract the video ID using yt-dlp's info extraction.
    Falls back to a hash of the URL if extraction fails.

    Args:
        url: Video URL (YouTube, Vimeo, etc.)

    Returns:
        Video ID string (always returns a valid identifier)
    """
    try:
        # Try to extract ID using yt-dlp
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
            info = ydl.extract_info(url, download=False, process=False)
            if info and "id" in info:
                return info["id"]
    except Exception:
        pass

    # Fall back to URL hash for caching
    return hashlib.md5(url.encode()).hexdigest()[:16]


def validateYouTubeUrl(url: str) -> bool:
    """Validate if a URL is a valid video URL.

    Note: Despite the function name (kept for backward compatibility),
    this now validates URLs for any video site supported by yt-dlp
    (YouTube, Vimeo, Dailymotion, etc.).

    Args:
        url: URL string to validate

    Returns:
        True if URL looks valid (basic format check), False otherwise
    """
    # Basic URL format validation - just check if it looks like a URL
    # Let yt-dlp handle the actual site support validation
    url = url.strip()
    return bool(re.match(r"^https?://", url, re.IGNORECASE)) or "." in url


def formatMetadata(metadata: Dict) -> str:
    """Format video metadata for user-friendly display.

    Args:
        metadata: Dictionary of video metadata from yt-dlp

    Returns:
        Formatted string with key video information
    """
    lines = []

    if title := metadata.get("title"):
        lines.append(f"'{title}'")

    if channel := metadata.get("channel") or metadata.get("uploader"):
        lines.append(f"{channel}")

    if duration := metadata.get("duration"):
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        lines.append(f"{minutes}m {seconds}s")

    if upload_date := metadata.get("upload_date"):
        # Format from YYYYMMDD to readable format
        if len(upload_date) == 8:
            formatted_date = f"{upload_date[0:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
            lines.append(f"{formatted_date}")

    if view_count := metadata.get("view_count"):
        lines.append(f"{view_count:,} view{'s' if view_count != 1 else ''}")

    return ", ".join(lines)


def getYouTubeSubtitles(url: str) -> Tuple[Optional[str], Dict]:
    """Extract subtitles/captions from video.

    Note: Despite the function name (kept for backward compatibility),
    this works with any video site that yt-dlp supports.

    Tries to get manual subtitles first (highest quality), then falls back
    to auto-generated captions. Much faster than audio transcription.

    Args:
        url: Video URL (YouTube, Vimeo, etc.)

    Returns:
        Tuple of (subtitle_text, metadata_dict)
        - subtitle_text: Cleaned subtitle text, or None if unavailable
        - metadata_dict: Video metadata including title, duration, channel, etc.

    Raises:
        ValueError: If URL is invalid
        RuntimeError: If extraction fails
        FileNotFoundError: If video is not accessible
    """
    # Validate URL
    if not validateYouTubeUrl(url):
        raise ValueError(f"Invalid video URL: {url}")

    # Configure yt-dlp to extract subtitle info
    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en.*"],  # Match any English variant
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            if info is None:
                raise RuntimeError("Failed to extract video information")

            # Extract metadata
            video_id = info.get("id", "unknown")
            metadata = {
                "title": info.get("title", "Unknown"),
                "channel": info.get("channel") or info.get("uploader", "Unknown"),
                "duration": info.get("duration", 0),
                "upload_date": info.get("upload_date", ""),
                "view_count": info.get("view_count", 0),
                "id": video_id,
                "url": url,
            }

            # Get available subtitles
            subtitles = info.get("subtitles", {})
            automatic_captions = info.get("automatic_captions", {})

            # Determine best subtitle to use
            # Priority: manual English > auto English > manual any > auto any
            subtitle_source = None
            subtitle_lang = None

            # Try manual English subtitles first
            for lang in ["en", "en-US", "en-GB", "en-CA", "en-AU"]:
                if lang in subtitles:
                    subtitle_source = subtitles[lang]
                    subtitle_lang = lang
                    metadata["subtitle_type"] = "manual"
                    break

            # Fall back to auto-generated English
            if not subtitle_source:
                for lang in ["en", "en-US", "en-GB", "en-CA", "en-AU"]:
                    if lang in automatic_captions:
                        subtitle_source = automatic_captions[lang]
                        subtitle_lang = lang
                        metadata["subtitle_type"] = "auto-generated"
                        break

            # Try any manual subtitles (prefer English-like codes)
            if not subtitle_source and subtitles:
                # Check for any English variant
                for lang in subtitles.keys():
                    if lang.startswith("en"):
                        subtitle_source = subtitles[lang]
                        subtitle_lang = lang
                        metadata["subtitle_type"] = "manual"
                        break

                # If still nothing, use first available
                if not subtitle_source:
                    subtitle_lang = list(subtitles.keys())[0]
                    subtitle_source = subtitles[subtitle_lang]
                    metadata["subtitle_type"] = "manual"

            # Try any auto-generated captions
            if not subtitle_source and automatic_captions:
                subtitle_lang = list(automatic_captions.keys())[0]
                subtitle_source = automatic_captions[subtitle_lang]
                metadata["subtitle_type"] = "auto-generated"

            # No subtitles available
            if not subtitle_source:
                metadata["subtitle_type"] = "none"
                return None, metadata

            metadata["subtitle_lang"] = subtitle_lang

            # Find the best subtitle format (prefer json3 for structured data)
            subtitle_url = None
            for sub_format in subtitle_source:
                if sub_format.get("ext") == "json3":
                    subtitle_url = sub_format.get("url")
                    break

            # Fall back to any available format
            if not subtitle_url and subtitle_source:
                subtitle_url = subtitle_source[0].get("url")

            if not subtitle_url:
                return None, metadata

            # Download subtitle content
            response = requests.get(subtitle_url, timeout=10)
            if not response.ok:
                raise RuntimeError(
                    f"Failed to download subtitles: HTTP {response.status_code}"
                )

            subtitle_content = response.text
            subtitle_format = subtitle_source[0].get("ext", "")

            # Check if content is an M3U8 playlist (common with Vimeo)
            if subtitle_content.strip().startswith("#EXTM3U"):
                # Parse M3U8 to extract actual subtitle URL
                vtt_url = _parse_m3u8_playlist(subtitle_content, subtitle_url)
                if vtt_url:
                    # Download the actual subtitle file
                    response = requests.get(vtt_url, timeout=10)
                    if response.ok:
                        subtitle_content = response.text
                        subtitle_format = (
                            "vtt"  # M3U8 playlists typically reference VTT files
                        )

            # Parse subtitle content based on format
            subtitle_text = _parse_subtitle_content(subtitle_content, subtitle_format)

            return subtitle_text, metadata

    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if "Private video" in error_msg or "not available" in error_msg:
            raise FileNotFoundError(f"Video not accessible: {error_msg}")
        raise RuntimeError(f"Subtitle extraction failed: {error_msg}") from e

    except requests.RequestException as e:
        raise RuntimeError(f"Failed to download subtitle data: {e}") from e

    except Exception as e:
        if isinstance(e, (ValueError, FileNotFoundError, RuntimeError)):
            raise
        raise RuntimeError(f"Unexpected error extracting subtitles: {e}") from e


def _parse_m3u8_playlist(m3u8_content: str, base_url: str) -> Optional[str]:
    """Parse M3U8 playlist to extract subtitle file URL.

    Args:
        m3u8_content: Raw M3U8 playlist content
        base_url: Base URL of the M3U8 file (for resolving relative URLs)

    Returns:
        Absolute URL to subtitle file, or None if not found
    """
    from urllib.parse import urljoin

    # Look for lines that don't start with # (these are the URLs)
    for line in m3u8_content.split("\n"):
        line = line.strip()
        if line and not line.startswith("#"):
            # Found a URL - resolve it relative to the M3U8 URL
            return urljoin(base_url, line)

    return None


def _parse_subtitle_content(content: str, format_ext: str) -> str:
    """Parse subtitle content from various formats.

    Args:
        content: Raw subtitle content
        format_ext: Format extension (json3, vtt, srv3, etc.)

    Returns:
        Cleaned subtitle text
    """
    if format_ext == "json3":
        # YouTube's JSON3 format with timestamps
        try:
            data = json.loads(content)
            text_parts = []

            if "events" in data:
                for event in data["events"]:
                    if "segs" in event:
                        for seg in event["segs"]:
                            if "utf8" in seg:
                                text_parts.append(seg["utf8"])

            return " ".join(text_parts).strip().replace("\n", " ")
        except json.JSONDecodeError:
            pass

    # For VTT, SRV3, or other text-based formats
    # Remove timestamps and formatting tags
    lines = []
    for line in content.split("\n"):
        line = line.strip()
        # Skip empty lines, timestamps, and metadata
        if not line or "-->" in line or line.startswith("WEBVTT") or line.isdigit():
            continue
        # Remove HTML-like tags
        line = re.sub(r"<[^>]+>", "", line)
        if line:
            lines.append(line)

    return " ".join(lines).strip()


def getYouTubeAudio(
    url: str,
    output_dir: str,
    max_duration: Optional[int] = None,
    max_size_mb: Optional[float] = None,
) -> Tuple[str, Dict]:
    """Download audio from video as MP3.

    Note: Despite the function name (kept for backward compatibility),
    this works with any video site that yt-dlp supports.

    Args:
        url: Video URL (YouTube, Vimeo, etc.)
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
        raise ValueError(f"Invalid video URL: {url}")

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

"""Video transcription plugin.

Downloads video audio from YouTube, Vimeo, and other sites using yt-dlp,
transcribes using configurable transcription backend (default: faster-whisper),
and generates LLM summaries by default. Use --transcript flag for full transcript.
"""

import tempfile
from pathlib import Path
import yt_dlp

from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend
from app.lib.youtube import (
    getYouTubeAudio,
    getYouTubeSubtitles,
    validateYouTubeUrl,
    formatMetadata,
    extractVideoId,
)
from app.lib.transcription import get_transcription_backend
from app.lib.cache import get_cache, set_cache
from app.lib.args import parse_arguments, help_arguments
from app.lib.network import depipeText
from .__PluginBase import PluginBase


# System prompt for generating summaries of transcripts
SUMMARY_SYSTEM_PROMPT = """
You are summarizing a transcript from a video. Provide a clear, concise summary that captures the main points and key takeaways. Focus on the most important information and structure it in a way that's easy to understand.

Keep the summary under 3-4 paragraphs unless there's significant complexity that requires more detail. Use plain text formatting.
"""

# Default cache TTL for transcripts (1 hour)
DEFAULT_TRANSCRIPT_CACHE_TTL = 3600
# Cache TTL for audio files (30 minutes - only kept if transcription fails)
DEFAULT_AUDIO_CACHE_TTL = 1800

ARG_SPECS = {
    "transcript": {
        "names": ["--transcript", "--transcribe", "-t"],
        "description": "Return full transcript text file (default: summary)",
        "type": bool,
    },
    "force_transcribe": {
        "names": ["--force-transcribe", "-f"],
        "description": "Force audio transcription (skip subtitle extraction)",
        "type": bool,
    },
    "help": {
        "names": ["--help", "-h"],
        "description": "Show this help message",
        "type": bool,
    },
}


def _extract_url(prompt: str) -> str:
    """Extract YouTube URL from prompt, handling Slack formatting.

    Args:
        prompt: User's prompt text

    Returns:
        Cleaned URL string

    Raises:
        ValueError: If no valid URL found
    """
    # First, handle Slack's pipe format using depipeText
    cleaned = depipeText(prompt)

    # Strip angle brackets if present (Slack format)
    cleaned = cleaned.strip().lstrip("<").rstrip(">")

    # Handle remaining pipe format (in case depipeText missed it)
    if "|" in cleaned:
        cleaned = cleaned.split("|", 1)[0]

    # Extract just the URL if there's additional text
    # Look for youtube.com or youtu.be patterns
    import re

    url_patterns = [
        r"(https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+(?:&[\w=&-]*)?)",
        r"(https?://(?:www\.)?youtube\.com/shorts/[\w-]+)",
        r"(https?://youtu\.be/[\w-]+)",
        r"(https?://(?:www\.)?youtube\.com/embed/[\w-]+)",
        r"(https?://(?:www\.)?youtube\.com/v/[\w-]+)",
    ]

    for pattern in url_patterns:
        match = re.search(pattern, cleaned)
        if match:
            return match.group(1)

    # If no pattern matched, return cleaned text and let validation catch it
    return cleaned.strip()


def _get_cache_key(video_id: str, cache_type: str = "transcript") -> str:
    """Generate cache key for a YouTube video.

    Args:
        video_id: YouTube video ID
        cache_type: Type of cache ("transcript" or "audio")

    Returns:
        Cache key string
    """
    return f"yt_{cache_type}_{video_id}"


def _get_config_values(backend: Ircawp_Backend) -> dict:
    """Extract YouTube-related config values from backend config.

    Args:
        backend: Backend instance with config

    Returns:
        Dict with config values (max_duration_minutes, max_size_mb, etc.)
    """
    youtube_config = backend.config.get("youtube", {})

    return {
        "max_duration_minutes": youtube_config.get("max_duration_minutes"),
        "max_size_mb": youtube_config.get("max_size_mb"),
        "cache_ttl_seconds": youtube_config.get(
            "cache_ttl_seconds", DEFAULT_TRANSCRIPT_CACHE_TTL
        ),
        "transcription_backend": youtube_config.get(
            "transcription_backend", "faster-whisper"
        ),
        "transcription_model": youtube_config.get("transcription_model"),
    }


def yt(
    prompt: str,
    media: list,
    backend: Ircawp_Backend,
    media_backend: MediaBackend = None,
) -> tuple[str, str, bool, dict]:
    """Main plugin function for YouTube transcription.

    Args:
        prompt: User's prompt containing YouTube URL
        media: List of media files (unused for this plugin)
        backend: LLM backend for summaries
        media_backend: Image generation backend (unused)

    Returns:
        Tuple of (response_text, media_path, skip_imagegen, metadata)
    """
    # Parse arguments
    prompt, config = parse_arguments(prompt, ARG_SPECS)

    # Show help if requested
    if config.get("help"):
        help_text = help_arguments(ARG_SPECS)
        usage_text = (
            "**YouTube Transcription Plugin**\n\n"
            "Downloads YouTube video audio and transcribes it. Attempts to use "
            "subtitles/captions first (fast), falls back to Whisper transcription.\n\n"
            "**Usage:** `/yt <youtube_url> [--summary] [--force-transcribe]`\n\n"
            "**Examples:**\n"
            "• `/yt https://youtube.com/watch?v=dQw4w9WgXcQ`\n"
            "• `/yt https://youtu.be/dQw4w9WgXcQ --summary`\n"
            "• `/yt <url> --force-transcribe` (skip subtitle extraction)\n\n"
            f"{help_text}"
        )
        return usage_text, "", True, {}

    # Extract URL from prompt
    try:
        url = _extract_url(prompt)
    except Exception as e:
        return f"Error extracting URL: {e}", "", True, {}

    # Validate URL
    if not validateYouTubeUrl(url):
        return (
            f"Invalid video URL: `{url}`\n\n"
            "Please provide a valid video URL (YouTube, Vimeo, etc.)",
            "",
            True,
            {},
        )

    # Extract video ID for caching
    video_id = extractVideoId(url)

    # Get config values
    cfg = _get_config_values(backend)
    transcript_cache_key = _get_cache_key(video_id, "transcript")
    audio_cache_key = _get_cache_key(video_id, "audio")

    # Check if transcript is already cached
    cached_data = get_cache(transcript_cache_key)
    if cached_data:
        backend.console.log(f"[green]Using cached transcript for video {video_id}")
        transcript = cached_data["transcript"]
        metadata = cached_data["metadata"]

        # If requesting full transcript, return snippet + file
        if config.get("transcript"):
            metadata_text = formatMetadata(metadata)

            # Create snippet (first 200 characters)
            snippet = transcript[:200] + ("..." if len(transcript) > 200 else "")

            # Create temporary text file with full transcript
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, prefix=f"transcript_{video_id}_"
            ) as f:
                f.write("YouTube Transcript\n")
                f.write(f"Video ID: {video_id}\n")
                f.write(f"Title: {metadata.get('title', 'Unknown')}\n")
                f.write(f"\n{'=' * 60}\n\n")
                f.write(transcript)
                transcript_file = f.name

            response = f"**YouTube Transcription**\n\n{metadata_text}\n\n**Transcript (first 200 chars):**\n```\n{snippet}\n```\n\n*Full transcript attached*"
            return response, transcript_file, True, {}

        # Otherwise (default), generate summary from cached transcript
        backend.console.log("[blue]Generating summary from cached transcript...")

        summary_prompt = f"Transcript from video '{metadata.get('title', 'Unknown')}':\n\n{transcript}"

        summary, _ = backend.runInference(
            system_prompt=SUMMARY_SYSTEM_PROMPT,
            prompt=summary_prompt,
            temperature=0.3,
            use_tools=False,
        )

        backend.console.log("[green]Summary generated")

        metadata_text = formatMetadata(metadata)
        response = f"**YouTube Transcription Summary**\n\n{metadata_text}\n\n**Summary:**\n{summary}"
        return response, "", True, {}

    # No cached transcript - need to get one
    try:
        transcript = None
        metadata = None
        transcription_method = None

        # Try subtitle extraction first (unless forced to transcribe)
        if not config.get("force_transcribe"):
            try:
                backend.console.log(
                    f"[blue]Attempting to extract subtitles from: {url}"
                )
                transcript, metadata = getYouTubeSubtitles(url)

                if transcript:
                    transcription_method = metadata.get("subtitle_type", "subtitle")
                    backend.console.log(
                        f"[green]Subtitles extracted ({transcription_method}, {len(transcript)} chars)"
                    )
                else:
                    backend.console.log(
                        "[yellow]No subtitles available, will use audio transcription"
                    )

            except Exception as e:
                backend.console.log(f"[yellow]Subtitle extraction failed: {e}")
                backend.console.log("[yellow]Falling back to audio transcription")

        # Fall back to audio transcription if subtitles not available
        if not transcript:
            # Check for cached audio or download new
            cached_audio_path = get_cache(audio_cache_key)
            audio_path = None
            audio_was_cached = False

            try:
                if cached_audio_path and Path(cached_audio_path).exists():
                    backend.console.log(
                        f"[green]Using cached audio for video {video_id}"
                    )
                    audio_path = cached_audio_path
                    audio_was_cached = True
                    # We need metadata, so we'll extract it during transcription
                    # For now, create a minimal metadata dict
                    metadata = {"id": video_id, "title": "Unknown"}
                else:
                    # Convert duration limit from minutes to seconds
                    max_duration = None
                    if cfg["max_duration_minutes"] is not None:
                        max_duration = cfg["max_duration_minutes"] * 60

                    # Download audio
                    backend.console.log(f"[blue]Downloading audio from: {url}")

                    # Use a persistent temp directory for caching
                    cache_dir = Path(tempfile.gettempdir()) / "ircawp_yt_cache"
                    cache_dir.mkdir(exist_ok=True)

                    audio_path, metadata = getYouTubeAudio(
                        url=url,
                        output_dir=str(cache_dir),
                        max_duration=max_duration,
                        max_size_mb=cfg["max_size_mb"],
                    )

                    backend.console.log(
                        f"[green]Downloaded: {metadata.get('title', 'Unknown')}"
                    )

                    # Cache the audio file path
                    set_cache(audio_cache_key, audio_path, ttl=DEFAULT_AUDIO_CACHE_TTL)

                # Transcribe audio
                backend.console.log("[blue]Transcribing audio with Whisper...")

                # Get transcription backend
                transcription_backend = get_transcription_backend(
                    backend_name=cfg["transcription_backend"],
                    model=cfg["transcription_model"],
                )

                # Transcribe audio
                transcript = transcription_backend.transcribe(audio_path)
                transcription_method = "whisper"

                backend.console.log(
                    f"[green]Transcription complete ({len(transcript)} chars)"
                )

                # If we used cached audio and don't have full metadata, try to extract it
                if audio_was_cached and metadata.get("title") == "Unknown":
                    try:
                        with yt_dlp.YoutubeDL(
                            {"quiet": True, "no_warnings": True}
                        ) as ydl:
                            info = ydl.extract_info(url, download=False)
                            if info:
                                metadata = {
                                    "title": info.get("title", "Unknown"),
                                    "channel": info.get("channel")
                                    or info.get("uploader", "Unknown"),
                                    "duration": info.get("duration", 0),
                                    "upload_date": info.get("upload_date", ""),
                                    "view_count": info.get("view_count", 0),
                                    "id": video_id,
                                    "url": url,
                                }
                    except Exception:
                        # If metadata extraction fails, use minimal metadata
                        pass

                # Delete the audio file and clear audio cache after successful transcription
                try:
                    if audio_path and Path(audio_path).exists():
                        Path(audio_path).unlink()
                        backend.console.log("[yellow]Deleted cached audio file")
                    # Clear audio cache entry
                    set_cache(audio_cache_key, None, ttl=0)
                except Exception as e:
                    backend.console.log(f"[yellow]Could not delete audio file: {e}")

            except Exception as e:
                # Audio transcription failed
                raise RuntimeError(f"Audio transcription failed: {e}") from e

        # At this point we have transcript and metadata (either from subtitles or Whisper)
        if not transcript or not metadata:
            raise RuntimeError("Failed to obtain transcript")

        # Add transcription method to metadata
        metadata["transcription_method"] = transcription_method

        # Cache the transcript
        cache_data = {"transcript": transcript, "metadata": metadata}
        set_cache(transcript_cache_key, cache_data, ttl=cfg["cache_ttl_seconds"])
        backend.console.log("[green]Transcript cached")

        # Format metadata for display
        metadata_text = formatMetadata(metadata)

        # Add transcription method note
        if transcription_method in ["manual", "auto-generated"]:
            method_note = f"\nTranscribed via {transcription_method} subtitles"
        else:
            method_note = "\nTranscribed via Whisper AI"

        # If requesting full transcript, return snippet + file
        if config.get("transcript"):
            snippet = transcript[:200] + ("..." if len(transcript) > 200 else "")

            # Create temporary text file with full transcript
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, prefix=f"transcript_{video_id}_"
            ) as f:
                f.write("YouTube Transcript\n")
                f.write(f"Video ID: {video_id}\n")
                f.write(f"Title: {metadata.get('title', 'Unknown')}\n")
                f.write(f"Method: {transcription_method or 'unknown'}\n")
                f.write(f"\n{'=' * 60}\n\n")
                f.write(transcript)
                transcript_file = f.name

            response = f"**YouTube Transcription**\n\n{metadata_text}{method_note}\n\n**Transcript (first 200 chars):**\n```\n{snippet}\n```\n\n*Full transcript attached*"
            return response, transcript_file, True, {}

        # Otherwise (default), generate summary
        backend.console.log("[blue]Generating summary...")

        summary_prompt = f"Transcript from video '{metadata.get('title', 'Unknown')}':\n\n{transcript}"

        summary, _ = backend.runInference(
            system_prompt=SUMMARY_SYSTEM_PROMPT,
            prompt=summary_prompt,
            temperature=0.3,
            use_tools=False,
        )

        backend.console.log("[green]Summary generated")

        response = f"\n\n{metadata_text}{method_note}\n\n*Summary:*\n{summary}"
        return response, "", True, {}

    except ValueError as e:
        # User-friendly errors (validation, limits, etc.)
        return f"❌ {str(e)}", "", True, {}

    except FileNotFoundError as e:
        # Video not accessible
        return f"❌ Video not accessible: {str(e)}", "", True, {}

    except ImportError as e:
        # Missing dependencies
        return (
            f"❌ Missing dependency: {str(e)}\n\n"
            "This plugin requires `yt-dlp`, `ffmpeg`, and `faster-whisper`.",
            "",
            True,
            {},
        )

    except RuntimeError as e:
        # Download or transcription failures
        return f"❌ Error: {str(e)}", "", True, {}

    except Exception as e:
        # Catch-all for unexpected errors
        backend.console.log(f"[red]Unexpected error in /yt: {e}")
        return f"❌ Unexpected error: {str(e)}", "", True, {}


# Plugin registration
plugin = PluginBase(
    name="Video Transcription",
    triggers=["yt", "youtube"],
    description="Transcribe and summarize videos (YouTube, Vimeo, etc.). Use --transcript for full text.",
    emoji_prefix="🎥",
    main=yt,
    prompt_required=True,
    media_required=False,
    msg_empty_query="Please provide a YouTube URL to transcribe",
)

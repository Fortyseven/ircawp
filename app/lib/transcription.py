"""Abstract transcription interface with swappable backends.

Provides a unified interface for audio transcription that allows easy switching
between different transcription services (lightwhisperstt, Whisper API, local Whisper, etc.).
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class TranscriptionBackend(ABC):
    """Abstract base class for audio transcription backends."""

    @abstractmethod
    def transcribe(self, audio_path: str) -> str:
        """Transcribe audio file to text.

        Args:
            audio_path: Path to audio file (typically MP3, WAV, etc.)

        Returns:
            Transcribed text

        Raises:
            FileNotFoundError: If audio file doesn't exist
            RuntimeError: If transcription fails
            ImportError: If required dependencies are missing
        """
        pass


class FasterWhisperBackend(TranscriptionBackend):
    """Transcription backend using faster-whisper library.

    This is an optimized implementation of Whisper that provides fast
    transcription with excellent accuracy.
    """

    def __init__(self, model: str = "base"):
        """Initialize FasterWhisper backend.

        Args:
            model: Model size to use (tiny, base, small, medium, large)
                   Default is "base" for balance of speed and accuracy
        """
        try:
            from faster_whisper import WhisperModel

            self.WhisperModel = WhisperModel
            self.model_name = model
            self.model = None  # Lazy load on first transcription
        except ImportError as e:
            raise ImportError(
                "faster-whisper not installed. Install with: pip install faster-whisper"
            ) from e

    def transcribe(self, audio_path: str) -> str:
        """Transcribe audio file using faster-whisper.

        Args:
            audio_path: Path to audio file

        Returns:
            Transcribed text

        Raises:
            FileNotFoundError: If audio file doesn't exist
            RuntimeError: If transcription fails
        """
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        try:
            # Lazy load model on first use
            if self.model is None:
                self.model = self.WhisperModel(
                    self.model_name, device="cpu", compute_type="int8"
                )

            # Transcribe audio file
            segments, info = self.model.transcribe(str(audio_file), beam_size=5)

            # Collect all text segments
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text)

            return " ".join(text_parts).strip()

        except Exception as e:
            raise RuntimeError(f"Transcription failed: {e}") from e


def get_transcription_backend(
    backend_name: Optional[str] = None, model: Optional[str] = None
) -> TranscriptionBackend:
    """Factory function to get configured transcription backend.

    Args:
        backend_name: Name of backend to use ("faster-whisper", etc.)
                      If None, defaults to "faster-whisper"
        model: Model size/name to use (backend-specific)
               If None, uses backend default

    Returns:
        Configured TranscriptionBackend instance

    Raises:
        ValueError: If backend_name is unknown
        ImportError: If backend dependencies are missing
    """
    if backend_name is None:
        backend_name = "faster-whisper"

    backend_name = backend_name.lower()

    if backend_name in ("faster-whisper", "faster_whisper", "fasterwhisper"):
        model = model or "base"
        return FasterWhisperBackend(model=model)
    else:
        raise ValueError(
            f"Unknown transcription backend: {backend_name}. Available: faster-whisper"
        )

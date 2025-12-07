"""
Transcribes text on a provided image.
"""

from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend
from .__PluginBase import PluginBase
from pydantic import BaseModel, Field


SYSTEM_PROMPT = """
Transcribe all of the legible text visible in the provided image. Skip any non-text elements. Skip any text that is not clearly legible.

Retain the original language. Do not translate. Just transcribe the text as accurately as possible in the original language.

If there are words difficult to transcribe due to illegibility, note this in the transcription using [???] next to the uncertain word.

Preserve layout formatting as best as possible, including line breaks, indentation, centering, and spacing.

Only return the transcribed text. Do not add any additional commentary or information."
""".strip()

DISABLE_IMAGEGEN = True


class TranscriptionResponse(BaseModel):
    """Structured response model for transcription output."""

    transcription_text: str = Field(..., description="The transcribed text.")
    cannot_transcribe: bool = Field(
        False, description="Indicates if the transcription could not be performed."
    )


def transcribe(
    prompt: str,
    media: list,
    backend: Ircawp_Backend,
    media_backend: MediaBackend = None,
) -> tuple[str, str, bool]:
    inf_response, _ = backend.runInference(
        system_prompt=SYSTEM_PROMPT,
        temperature=0.2,
        media=media,
        use_tools=False,
    )

    return (f"```{inf_response}```", "", DISABLE_IMAGEGEN, {})


plugin = PluginBase(
    name="Transcribe text",
    description="Transcribes the given text.",
    triggers=["transcribe"],
    system_prompt="",
    emoji_prefix="📃",
    msg_exception_prefix="TRANSCRIPTION PROBLEMS",
    main=transcribe,
    use_imagegen=False,
    prompt_required=False,
    media_required=True,
)

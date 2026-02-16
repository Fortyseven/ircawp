"""
Transcribes text on a provided image.
"""

from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend
from .__PluginBase import PluginBase
from pydantic import BaseModel, Field


SYSTEM_PROMPT = """
{}

Transcribe all of the legible text visible in the provided image. Skip any non-text elements. Skip any text that is not clearly legible.

If there are words difficult to transcribe due to illegibility, note this in the transcription using [???] next to the uncertain word.

Preserve layout formatting as best as possible, including line breaks, indentation, centering, and spacing.

Unless the user requests otherwise, retain the original language and do not translate unless requested; just transcribe the text as accurately as possible in the original language."
""".strip()

DISABLE_IMAGEGEN = True


class TranscriptionResponse(BaseModel):
    """Structured response model for transcription output."""

    transcription_text: str = Field(
        ...,
        description="The transcribed text, with optional user requested modifications.",
    )
    cannot_transcribe: bool = Field(
        False, description="Indicates if the transcription could not be performed."
    )


def transcribe(
    prompt: str,
    media: list,
    backend: Ircawp_Backend,
    media_backend: MediaBackend = None,
) -> tuple[str, str, bool]:
    sysprompt = SYSTEM_PROMPT.format(
        f"User requested modifications (overrides default behavior): {prompt}"
        if prompt
        else ""
    )
    backend.console.log(
        "[black on green]= Transcribe plugin system prompt: ", sysprompt
    )
    inf_response, _ = backend.runInference(
        system_prompt=sysprompt,
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

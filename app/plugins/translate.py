"""
Provides a language translation to English.
"""

from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend
from .__PluginBase import PluginBase
from pydantic import BaseModel, Field


SYSTEM_PROMPT = """
You are a world class language translator.

Translate the provided text into English. Translate the entire provided text.

If you cannot confidently and correctly translate the text, please respond with "I cannot confidently translate this text."

Provide the source language if you can detect it, along with an appropriate flag emoji representing that language if possible.

Optionally add any notes that might help give context for the translation. Do not invent or guess at a word's meaning. If you are unsure of a word's meaning, you may provide a literal translation of the word.
"""

DISABLE_IMAGEGEN = True


class TranslationResponse(BaseModel):
    """Structured response model for translation output."""

    translation: str = Field(..., description="The translated text in English.")
    source_language: str | None = Field(
        None, description="The detected source language of the input text."
    )
    language_flag_emoji: str | None = Field(
        None, description="The emoji flag representing the source language."
    )
    notes: str | None = Field(None, description="Additional notes for context.")
    cannot_translate: bool = Field(
        False, description="Indicates if the translation could not be performed."
    )


def translate(
    prompt: str,
    media: list,
    backend: Ircawp_Backend,
    media_backend: MediaBackend = None,
) -> tuple[str, str, bool]:
    inf_response, _ = backend.runInference(
        system_prompt=SYSTEM_PROMPT,
        prompt=prompt.strip(),
        format=TranslationResponse,
        temperature=0.2,
        use_tools=False,
    )

    if_response = TranslationResponse.model_validate_json(inf_response)

    if if_response.cannot_translate:
        return (
            "I cannot confidently translate this text.",
            "",
            DISABLE_IMAGEGEN,
        )

    final_response = f"*{if_response.source_language or 'Unknown'}* {if_response.language_flag_emoji or ''}:\n> _{if_response.translation}_"
    if if_response.notes:
        final_response += f"\n\n*Notes:* _{if_response.notes}_"

    backend.console.log("Translation completed")
    return (
        final_response,
        "",
        DISABLE_IMAGEGEN,
    )


plugin = PluginBase(
    name="Translate text",
    description="Translates the given text to English.",
    triggers=["translate"],
    system_prompt="",
    emoji_prefix="",
    msg_empty_query="No prompt provided",
    msg_exception_prefix="TRANSLATING PROBLEMS",
    main=translate,
    use_imagegen=True,
    prompt_required=True,
)

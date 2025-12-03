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

If there are words difficult to translate due to illegibility, note this in the translation using [???] next to the uncertain word.

Optionally provide a summary of the translation in 1-2 sentences if the text is long or complex.

Provide the source language if you can detect it, along with an appropriate flag emoji representing that language if possible.

Optionally add any notes that might help give context for the translation. Do not invent or guess at a word's meaning. If you are unsure of a word's meaning, you may provide a literal translation of the word.
"""

DISABLE_IMAGEGEN = True


def format_translation_as_quote(text: str) -> str:
    """
    Wraps translation text in markdown quote formatting.
    Handles multi-line text by prefixing each line with '>'.

    Args:
        text: The translation text to format

    Returns:
        The formatted text with markdown quote syntax
    """
    lines = text.split("\n")
    formatted_lines = [f"> _{line}_" for line in lines]
    return "\n".join(formatted_lines)


class TranslationResponse(BaseModel):
    """Structured response model for translation output."""

    translation: str = Field(..., description="The translated text in English.")
    source_language: str | None = Field(
        None, description="The detected source language of the input text."
    )
    language_flag_emoji: str | None = Field(
        None, description="The emoji flag representing the source language."
    )
    summary: str | None = Field(None, description="A brief summary of the translation.")
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
        media=media,
        use_tools=False,
    )

    try:
        if_response = TranslationResponse.model_validate_json(inf_response)
    except Exception as e:
        # Handle JSON truncation or parsing errors
        return (
            f"Translation failed due to response truncation or parsing error. The text may be too long. Error: {str(e)[:100]}",
            "",
            DISABLE_IMAGEGEN,
        )

    if if_response.cannot_translate:
        return ("I cannot confidently translate this text.", "", DISABLE_IMAGEGEN, {})

    translated_text = format_translation_as_quote(if_response.translation)
    final_response = f"*{if_response.source_language or 'Unknown'}* {if_response.language_flag_emoji or ''}:\n{translated_text}"

    if if_response.summary:
        final_response += f"\n\n*Summary:* _{if_response.summary}_"
    if if_response.notes:
        final_response += f"\n\n*Notes:* _{if_response.notes}_"

    return (final_response, "", DISABLE_IMAGEGEN, {})


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

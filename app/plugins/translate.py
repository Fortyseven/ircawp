"""
Provides a language translation to English.
"""

from app.backends.Ircawp_Backend import Ircawp_Backend
from .__PluginBase import PluginBase


SYSTEM_PROMPT = """
You are a world class language translator.

Translate the provided text into English. Translate the entire provided text.

If you cannot confidently and correctly translate the text, please respond with "I cannot confidently translate this text."

Also add notes that might help give context for the translation. Do not invent or guess at a word's meaning. If you are unsure of a word's meaning, you may provide a literal translation of the word.

Respond ONLY with a properly structured Markdown like this:

Translation:

From $LANGUAGE:
>  *$ENGLISH_TRANSLATION*

Notes: $TRANSLATION_NOTES
"""

DISABLE_IMAGEGEN = True


def translate(
    prompt: str, media: list, backend: Ircawp_Backend
) -> tuple[str, str, bool]:
    inf_response = backend.runInference(
        system_prompt=SYSTEM_PROMPT,
        prompt=prompt.strip(),
    )

    return (
        # f"Top stories from Hacker News as of {START_TIME.strftime('%Y-%m-%d %H:%M:%S')}"
        # + "\n".join(
        #     [
        #         f"{i + 1}. {feed.entries[i].title} - {feed.entries[i].link}"
        #         for i in range(5)
        #     ]
        # ),
        # "",
        inf_response,
        "",
        DISABLE_IMAGEGEN,
    )


plugin = PluginBase(
    name="Translate HTML",
    description="Translates the given HTML URL to English.",
    triggers=["translate"],
    system_prompt="",
    emoji_prefix="",
    msg_empty_query="No prompt provided",
    msg_exception_prefix="TRANSLATING PROBLEMS",
    main=translate,
    use_imagegen=True,
    prompt_required=True,
)

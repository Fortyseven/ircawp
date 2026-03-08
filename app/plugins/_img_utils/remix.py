from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend


def subcommand_remix(
    prompt: str,
    media: list,
    backend: Ircawp_Backend,
    media_backend: MediaBackend = None,
) -> tuple[str, str, bool]:
    SPROMPT = """
You are an expert at solving Wordle puzzles. Given an image of a Wordle game board, extract the letters and their colors (green, yellow, gray) and provide the next best guess word based on the current state of the board.
"""

    # ensure one image is provided
    if not media or len(media) != 1:
        return (
            "Remix subcommand requires exactly one input image.",
            "",
            False,
            {},
        )

    # run inference to extract letters from image

    response, _ = backend.runInference(
        system_prompt=SPROMPT,
        # prompt=text,
        media=media,
        use_tools=False,
        temperature=0.1,
    )

    # Combine extracted words and alley count in the response
    return (
        f"Extracted words: `{', '.join(words.words)}` | Alley count: {alley_count}",
        bar,
        False,
        {},
    )

from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend
from .batch import doBatchImages


def subcommand_wordle(
    prompt: str,
    media: list,
    backend: Ircawp_Backend,
    media_backend: MediaBackend = None,
) -> tuple[str, str, bool]:
    from pydantic import BaseModel

    class WordleWordsResponse(BaseModel):
        words: list[str] = []

    class WordleAlleyCountResponse(BaseModel):
        alley_count: int = 0

    SPROMPT = """
You are an expert at solving Wordle puzzles. Given an image of a Wordle game board, extract the letters and their colors (green, yellow, gray) and provide the next best guess word based on the current state of the board.
"""

    ALLEY_ANALYSIS_PROMPT = """
Analyze the composite image, which contains four distinct scenes. For each scene, determine if it depicts a street alley—defined as a narrow passage between buildings in an urban setting, with paved ground and structures on both sides. If it looks like a wide alley, it is likely a street and not actually an alley. If you are uncertain, do not count it as an alley. Only count an alley if you are 100% certain. Count the total number of scenes that meet this definition. Return only the numeric count of alleys found.
"""

    # ensure one image is provided
    if not media or len(media) != 1:
        return (
            "Wordle subcommand requires exactly one input image.",
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
        format=WordleWordsResponse,
        temperature=0.1,
    )

    # print(response)

    words = WordleWordsResponse.model_validate_json(response)

    config = {"batch": 4, "aspect": "4:3"}

    batch = doBatchImages(" ".join(words.words), [], backend, media_backend, config)

    # add extracted words to the response
    foo, bar, baz, quux = batch

    # If grid generation failed, return error
    if baz:
        return (
            "Failed to generate image grid for wordle subcommand.",
            "",
            # bar,
            baz,
            quux,
        )

    # Grid was successful, now analyze it for alleys
    try:
        alley_response, _ = backend.runInference(
            system_prompt=ALLEY_ANALYSIS_PROMPT,
            media=[bar],  # bar is the grid_path
            use_tools=False,
            format=WordleAlleyCountResponse,
            temperature=0.1,
        )
        alley_data = WordleAlleyCountResponse.model_validate_json(alley_response)
        alley_count = alley_data.alley_count
    except Exception as e:
        backend.console.log(f"[yellow on black] Alley analysis failed: {e}")
        return (
            f"Extracted words: `{', '.join(words.words)}` | Alley analysis failed.",
            bar,
            False,
            quux,
        )

    # Combine extracted words and alley count in the response
    return (
        f"Extracted words: `{', '.join(words.words)}` | Alley count: {alley_count}",
        bar,
        False,
        {},
    )

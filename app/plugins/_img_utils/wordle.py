from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend
from .batch import doBatchImages
from pydantic import BaseModel
from PIL import Image, ImageOps


# disable image generation and just return the extracted words for testing
DEBUG = False


PREPROCESSED_PATH = "/tmp/ircawp.wordle_preprocessed.png"


def preprocess_wordle_image(image_path: str) -> str:
    """Binarize a Wordle board: grayscale → autocontrast → threshold.
    Strips cell colors so the LLM focuses only on letter shapes.
    File is left in /tmp for debugging. Raises on failure.
    """
    img = Image.open(image_path).convert("L")
    img = ImageOps.autocontrast(img, cutoff=2)
    img = img.point(lambda p: 255 if p > 180 else 0, mode="1")
    img = img.convert("RGB")
    img.save(PREPROCESSED_PATH, format="PNG")
    return PREPROCESSED_PATH


class WordleWordsResponse(BaseModel):
    words: list[str] = []


class WordleAlleyCountResponse(BaseModel):
    alley_count: int = 0


def extract_words(backend: Ircawp_Backend, media: list) -> list[str]:
    SPROMPT = """You are an expert at parsing Wordle game boards.
Your task is to extract each horizontal word from every filled row in the grid,
reading left to right. Empty rows (no letters) must be skipped.

Rules:
- Every Wordle word is EXACTLY 5 letters. Count each letter individually before outputting.
- Do NOT truncate or drop any letters — if you see 5 letter shapes in a row, output all 5.
- Do NOT exceed 5 letters per word, even if the image is messy. If you see more than 5 letter shapes in a row, only output the first 5.
- Do NOT output any words that are not exactly 5 letters. If a row contains fewer than 5 letter shapes, skip it entirely.
- Output only the words, one per line, no explanations or extra text.
"""

    # Preprocess: strip cell colors, leaving only letter shapes
    preprocessed_media = media
    try:
        preprocessed_media = [preprocess_wordle_image(media[0])]
    except Exception as e:
        backend.console.log(f"[yellow]Wordle preprocessing failed, using original: {e}")

    response, _ = backend.runInference(
        system_prompt=SPROMPT,
        prompt="Extract all words from this Wordle board. Each word must be exactly 5 letters.",
        media=preprocessed_media,
        use_tools=False,
        format=WordleWordsResponse,
        temperature=0.1,
    )

    # print(response)

    return WordleWordsResponse.model_validate_json(response).words


def subcommand_wordle(
    prompt: str,
    media: list,
    backend: Ircawp_Backend,
    media_backend: MediaBackend = None,
) -> tuple[str, str, bool]:
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

    words = extract_words(backend, media)

    if DEBUG:
        return (
            f"Extracted words: `{', '.join(words)}` | [DEBUG MODE: Skipping grid generation and alley analysis]",
            "",
            False,
            {},
        )

    config = {"batch": 4, "aspect": "4:3"}

    batch = doBatchImages(" ".join(words), [], backend, media_backend, config)

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
            f"Extracted words: `{', '.join(words)}` | Alley analysis failed.",
            bar,
            False,
            quux,
        )

    # Combine extracted words and alley count in the response
    return (
        f"Extracted words: `{', '.join(words)}` | Alley count: {alley_count}",
        bar,
        False,
        {},
    )

"""
Provides a language translation to English.
"""

from app.backends.Ircawp_Backend import Ircawp_Backend
from .__PluginBase import PluginBase


SYSTEM_PROMPT = """
You are an expert geolocation investigator who can figure out where a photo is from the clues present in the image.

Enumerate every element and clue in the image and think about them step-by-step, analyzing every detail in the image. Create a list of potential locations the image might be depicting. Include a confidence percentage for each.

Take advantage of colors, details on objects, cultural norms, text on signs, and any other clues. Try to think outside the box for clues.

It is an acceptable outcome to not have enough information to geolocate an image. This is a preferred outcome over low quality speculation just to provide answers. This is important.

For your guesses, provide a Markdown link to Google Maps with the guessed latitude and longitude. Follow this example to create the link: https://www.google.com/maps/place/28%C2%B059'54.7%22N+50%C2%B022'14.8%22E
"""

DISABLE_IMAGEGEN = True


def geolocate(
    prompt: str, media: list, backend: Ircawp_Backend
) -> tuple[str, str, bool]:
    backend.console.log(f"Geolocate plugin invoked with prompt: {media}")
    if not media or len(media) == 0:
        return "No image provided for geolocation.", "", DISABLE_IMAGEGEN

    inf_response = backend.runInference(
        system_prompt=SYSTEM_PROMPT, prompt=prompt.strip(), media=media, temperature=0.2
    )

    return (
        inf_response,
        "",
        DISABLE_IMAGEGEN,
    )


plugin = PluginBase(
    name="Geolocate by Image",
    description="Attempts to geolocate a provided image",
    triggers=["geolocate"],
    system_prompt="",
    emoji_prefix="",
    msg_empty_query="No prompt provided",
    msg_exception_prefix="GEOLOCATING PROBLEMS",
    main=geolocate,
    use_imagegen=False,
    prompt_required=True,
)

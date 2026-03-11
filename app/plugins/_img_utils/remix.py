from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend
from .single import (
    doSingleImage,
    getRedoPrompt,
    getRedoMedia,
    getMediaAspectRatio,
    saveRedoMedia,
)


def subcommand_remix(
    prompt: str,
    media: list,
    backend: Ircawp_Backend,
    media_backend: MediaBackend = None,
    config: dict = None,
) -> tuple[str, str, bool]:
    backend.console.log("[cyan on black] executing --remix subcommand")
    SPROMPT = """
This high-angle, aerial photograph captures a dramatic maritime emergency featuring a large tanker vessel engulfed in flames amidst a vast expanse of deep blue ocean. The image is rendered with the clarity of a digital capture or high-resolution photo, characterized by naturalistic lighting and high contrast between the bright blue water and the dark, choking smoke. The composition is dominated by the ship, which is oriented diagonally across the frame, extending from the lower right towards the upper left, creating a strong leading line that draws the eye into the scene. The ship itself is a massive tanker with a black hull and a reddish-brown upper deck structure; the deck is cluttered with complex piping, white structural elements, and small equipment, though the specific details are somewhat distant. A fierce fire erupts from the mid-to-aft section of the vessel, specifically near the bridge or accommodation block, sending bright orange and yellow flames licking upward along the starboard side of the ship's superstructure. Rising from this fire is a voluminous, dense column of thick, black smoke that billows upward and drifts toward the upper left of the frame, expanding into a turbulent, cloud-like mass that obscures the sky behind it. The smoke is highly textured, showing distinct layers and clumps of particulate matter, and casts a dark shadow over the aft section of the ship. The surrounding water is a deep, saturated azure blue, textured with gentle ripples and small whitecaps, indicating a moderate breeze. The ship creates a subtle wake, and white water can be seen churning near the bow, suggesting the vessel is either moving slowly or being buffeted by the sea. The horizon line is visible in the distance, separating the blue ocean from a pale, slightly hazy blue sky. At the very bottom of the frame, partially cut off, there is text in a yellow, bold font with a black outline, though only the tops of the letters are visible, rendering the specific words illegible. The overall atmosphere is one of urgency, destruction, and environmental hazard, emphasized by the stark contrast between the serene blue sea and the violent, black plume of pollution.
""".strip()

    if config.get("redo", False):
        # if getLastRefinedPrompt() is None:
        #     return (
        #         "No previous refined prompt to use for --again. Run `/img` first.",
        #         "",
        #         False,
        #         {},
        #     )
        prompt = getRedoPrompt()
        media = getRedoMedia()

        print("HEY ARE WE HERE?\n\n\n\n")

        if not media or len(media) != 1:
            return (
                "No previous media found for --again. Run `/img --remix` with an image first.",
                "",
                False,
                {},
            )
        backend.console.log(
            "[cyan on black] using last refined prompt/media for --remix --again"
        )

    # ensure one image is provided
    if not media or len(media) != 1:
        return (
            "--remix requires exactly one input image.",
            "",
            False,
            {},
        )

    response, _ = backend.runInference(
        system_prompt=SPROMPT,
        prompt=prompt,
        media=media,
        use_tools=False,
        temperature=0.8,
    )

    source_aspect = getMediaAspectRatio(media[0])

    saveRedoMedia(media)

    return doSingleImage(
        response,
        [],
        backend,
        media_backend,
        config={"aspect": source_aspect},
    )

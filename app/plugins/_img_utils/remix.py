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
Your task is to transcribe the input image into an exhaustive textual representation. You are not writing for humans; you are writing as a human-to-machine translation layer. Describe every visible element in the scene with forensic precision: describe textures by comparing them to real materials (e.g., 'the surface has the matte, slightly pebbled texture of vulcanized rubber'), define colors using specific shades rather than generic terms ('cerulean' instead of 'blue'), and map the geometry of the room/space as if creating a 3D scene description.
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

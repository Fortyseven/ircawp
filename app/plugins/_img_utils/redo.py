from pathlib import Path

from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend

from .single import getRedoPrompt, doRedoImage


def submodule_redo(
    prompt: str,
    media: list,
    backend: Ircawp_Backend,
    media_backend: MediaBackend,
    config: dict,
) -> tuple[str, str, bool, dict]:
    # Validate: no new prompt provided (after flag parsing)
    if prompt and prompt.strip():
        return (
            "Cannot combine --redo with a new prompt. Use `/img --redo` alone.",
            "",
            False,
            {},
        )

    # Validate: no new media provided
    if media:
        return (
            "Cannot combine --redo with new media. Use `/img --redo` alone.",
            "",
            False,
            {},
        )

    # Validate: no other conflicting flags
    conflicting = [k for k in ["andthen", "wordle"] if config.get(k)]
    if conflicting:
        return (
            f"Cannot combine --redo with other flags: {', '.join(conflicting)}",
            "",
            False,
            {},
        )

    # Check if we have saved state
    if not getRedoPrompt():
        return (
            "No previous generation to redo. Run `/img` first.",
            "",
            False,
            {},
        )

    # # Verify saved media files still exist
    # for media_path in getRedoMedia() or []:
    #     if not Path(media_path).is_file():
    #         return (
    #             f"Redo media file missing: {media_path}",
    #             "",
    #             False,
    #             {},
    #         )

    # Restore state (overwrites parsed values)
    # prompt = getRedoPrompt()
    # media = getRedoMedia()
    # config = last_redo_config.copy()  # Copy to avoid mutation
    backend.console.log("[cyan on black] loaded redo state from memory")

    return doRedoImage(backend, media_backend)

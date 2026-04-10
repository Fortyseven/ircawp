import shutil
import glob
from pathlib import Path
from PIL import Image

from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend

from .paths import LAST_GENERATED_IMAGE_PATH, REDO_MEDIA_PATH_PREFIX
# , UNDO_IMAGE_PATH

last_refined_prompt: str = None
last_redo_prompt: str = None
last_redo_media: list = []
last_redo_config: dict = {}


def setLastRefinedPrompt(prompt: str):
    global last_refined_prompt
    last_refined_prompt = prompt


def getLastRefinedPrompt() -> str:
    global last_refined_prompt
    return last_refined_prompt


# -------------------------------------


def setRedoPrompt(prompt: str):
    global last_redo_prompt
    last_redo_prompt = prompt


def getRedoPrompt() -> str:
    global last_redo_prompt
    return last_redo_prompt


# -------------------------------------


def setRedoConfig(config: dict):
    global last_redo_config
    last_redo_config = config.copy()  # Copy to avoid external mutations


def getRedoConfig() -> dict:
    global last_redo_config
    return last_redo_config.copy()  # Copy to avoid external mutations


# -------------------------------------

# def getUndoMedia() -> list:
#     return [UNDO_IMAGE_PATH] if Path(UNDO_IMAGE_PATH).is_file() else []


def setLastGeneratedMedia(image_path: str):
    # new generated image -> shift current last to undo, then set new last
    # if Path(LAST_GENERATED_IMAGE_PATH).is_file():
    #     shutil.copy(LAST_GENERATED_IMAGE_PATH, UNDO_IMAGE_PATH)

    shutil.copy(image_path, LAST_GENERATED_IMAGE_PATH)


def getLastGeneratedMediaPath() -> str:
    if Path(LAST_GENERATED_IMAGE_PATH).is_file():
        return LAST_GENERATED_IMAGE_PATH
    return None


def getLastGeneratedMedia() -> list:
    return (
        [LAST_GENERATED_IMAGE_PATH] if Path(LAST_GENERATED_IMAGE_PATH).is_file() else []
    )


###############################################################################


def _cleanup_redo_media() -> None:
    """Remove old redo media files to prevent accumulation."""
    try:
        for old_file in glob.glob(f"{REDO_MEDIA_PATH_PREFIX}_*"):
            Path(old_file).unlink(missing_ok=True)
    except Exception:
        pass  # Silently ignore cleanup errors


def getRedoMedia() -> list:
    print("DEBUG: getRedoMedia", last_redo_media)
    return last_redo_media


def saveRedoMedia(media: list) -> list:
    """Save media files to persistent temp paths for --redo functionality.

    Args:
        media: List of media file paths (will be deleted after plugin execution)

    Returns:
        List of persistent paths in /tmp/ircawp.redo_media_* format
    """
    global last_redo_media

    if not media:
        return []

    # Clean up old redo media files first
    _cleanup_redo_media()

    persistent_paths = []
    for i, media_path in enumerate(media):
        try:
            # Get file extension from original path
            ext = Path(media_path).suffix or ".png"
            persistent_path = f"{REDO_MEDIA_PATH_PREFIX}_{i}{ext}"

            # Copy to persistent location
            shutil.copy(media_path, persistent_path)
            persistent_paths.append(persistent_path)
        except Exception:
            # If we fail to save any media, bail out
            return []

    last_redo_media = persistent_paths

    return persistent_paths


###############################################################################


def getMediaAspectRatio(media_path: str) -> float:
    """Extract aspect ratio (width/height) from an image file."""
    try:
        img = Image.open(media_path)
        return img.width / img.height
    except Exception:
        return None


###############################################################################
###############################################################################


def doRedoImage(
    backend: Ircawp_Backend, media_backend: MediaBackend
) -> tuple[str, str, bool, dict]:
    prompt = getRedoPrompt()
    media = getRedoMedia()
    config = getRedoConfig()

    return doSingleImage(prompt, media, backend, media_backend, config)


def _handleAspect(config: dict, media: list, backend: Ircawp_Backend):
    ### ASPECT
    # Handle --aspect match: if aspect is "match" (or not specified),
    # automatically set aspect to the media's aspect ratio

    aspect_value = config.get("aspect")

    if aspect_value == "match" or aspect_value is None:
        media_aspect = getMediaAspectRatio(media[0])
        print("DEBUG: media_aspect", media_aspect)
        if media_aspect is not None:
            config["aspect"] = media_aspect
            if aspect_value is None:
                backend.console.log(
                    f"[cyan on black] defaulting to media aspect ratio: {media_aspect:.2f}"
                )
            else:
                backend.console.log(
                    f"[cyan on black] matched media aspect ratio: {media_aspect:.2f}"
                )


def doSingleImage(
    prompt: str,
    media: list,
    backend: Ircawp_Backend,
    media_backend: MediaBackend,
    config: dict,
) -> tuple[str, str, bool, dict]:
    setRedoPrompt(prompt)  # for --redo
    saveRedoMedia(media)  # for --redo
    setRedoConfig(config)

    if prompt.startswith("!"):
        backend.console.log("[white on green] skipping prompt refinement")
        config["skip_refinement"] = True
        prompt = prompt[1:]

    print("DEBUG: config", config, media)

    if media:
        _handleAspect(config, media, backend)

    print("DEBUG: config", config)

    ### BATCH
    if config.get("batch", 1) > 4:
        config["batch"] = 4

    if config.get("batch", 1) > 1:
        from .batch import doBatchImages

        return doBatchImages(prompt, media, backend, media_backend, config)

    ###########

    image_path, final_prompt = media_backend.execute(
        prompt=prompt, config=config, media=media, backend=backend
    )

    setLastRefinedPrompt(final_prompt)  # for --again
    setLastGeneratedMedia(image_path)

    return "", image_path, False, {"imagegen_prompt": final_prompt}

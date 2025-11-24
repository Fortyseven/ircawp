"""
Bot plugin that allows the user to ask a raw prompt of the LLM without a system preamble.
"""

import os
from uuid import uuid4
from app.backends.Ircawp_Backend import Ircawp_Backend
from app.types import InfResponse
from .__PluginBase import PluginBase

from .vendor.xtts_api_server.tts_funcs import TTSWrapper

# defaults
DEVICE = "cpu"
OUTPUT_FOLDER = "/tmp"
SPEAKER_FOLDER = f"{os.path.dirname(__file__)}/vendor/xtts_api_server/speakers"
MODEL_FOLDER = f"{os.path.dirname(__file__)}/vendor/xtts_api_server/xtts_models"
MODEL_SOURCE = os.getenv("MODEL_SOURCE", "local")
MODEL_VERSION = os.getenv("MODEL_VERSION", "v2.0.2")
LOWVRAM_MODE = os.getenv("LOWVRAM_MODE") == "true"
DEEPSPEED = False
USE_CACHE = os.getenv("USE_CACHE") == "true"

XTTS: TTSWrapper = TTSWrapper(
    OUTPUT_FOLDER,
    SPEAKER_FOLDER,
    MODEL_FOLDER,
    LOWVRAM_MODE,
    MODEL_SOURCE,
    MODEL_VERSION,
    DEVICE,
    DEEPSPEED,
    USE_CACHE,
)


def initTTS(backend: Ircawp_Backend):
    """
    Initialize the plugin.
    """
    print("Initializing saysforty plugin.", SPEAKER_FOLDER)

    global XTTS, MODEL_VERSION

    XTTS.model_version = XTTS.check_model_version_old_format(MODEL_VERSION)
    MODEL_VERSION = XTTS.model_version

    print("Loading model version", MODEL_VERSION)

    XTTS.load_model()


def saysforty(prompt: str, media: list, backend: Ircawp_Backend) -> InfResponse:
    # return prompt.strip(), ""
    # response = backend.runInference(
    #     system_prompt="", user_prompt=prompt.strip()
    # )
    # breakpoint()
    # XTTS.api_generation(prompt, "47", "en", "/tmp/ircawp-saysforty.wav")

    try:
        # Generate an audio file using process_tts_to_file.
        output_file_path = XTTS.process_tts_to_file(
            text=prompt,
            speaker_name_or_path="47",
            language="en",
            # file_name_or_path=f"{str(uuid4())}.wav",
            file_name_or_path="/tmp/ircawp-saysforty.wav",
        )

        # if not XTTS.enable_cache_results:
        #     background_tasks.add_task(os.unlink, output_file_path)

        # # Return the file in the response
        # return FileResponse(
        #     path=output_file_path,
        #     media_type='audio/wav',
        #     filename="output.wav",
        #     )

    except Exception as e:
        print(e)

    return "", "/tmp/ircawp-saysforty.wav", True


plugin = PluginBase(
    name="Make Fortyseven say something.",
    description="Pass text for Fortyseven to say.",
    triggers=["saysforty"],
    system_prompt="",
    emoji_prefix="",
    msg_empty_query="No text provided",
    msg_exception_prefix="FORTY PROBLEMS",
    init=initTTS,
    main=saysforty,
    use_imagegen=False,
)

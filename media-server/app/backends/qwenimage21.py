"""Qwen-Image-2.1 backend for media-server.

Uses a GGUF 4-bit quantized transformer (self-quantized from the official
Qwen/Qwen-Image-2.1 weights via scripts/convert_qwenimage21_to_gguf.py +
llama-quantize) with the text encoder (4-bit bitsandbytes) and VAE from the
base Qwen/Qwen-Image-2.1 repo.

Prompt refinement is handled by the client (ircawp bot).
This backend receives a final, ready-to-use prompt.
"""

from .MediaBackend import MediaBackend

import os

import torch
from diffusers import QwenImage21Pipeline
from diffusers.quantizers.quantization_config import GGUFQuantizationConfig
from diffusers.utils import load_image


def _register_qwenimage21_single_file():
    """Register QwenImage21Transformer2DModel for from_single_file loading.

    The 2.1 transformer class is not in diffusers' SINGLE_FILE_LOADABLE_CLASSES
    compatibility list, so from_single_file raises ValueError. The mapping for
    QwenImageTransformer2DModel is an identity checkpoint mapping, which is
    exactly what we need for the GGUF state dict, so we register the same
    mapping for the 2.1 class.
    """
    from diffusers import QwenImage21Transformer2DModel
    from diffusers.loaders.single_file_model import SINGLE_FILE_LOADABLE_CLASSES

    if "QwenImage21Transformer2DModel" not in SINGLE_FILE_LOADABLE_CLASSES:
        SINGLE_FILE_LOADABLE_CLASSES["QwenImage21Transformer2DModel"] = {
            "checkpoint_mapping_fn": lambda checkpoint, **kwargs: checkpoint,
            "default_subfolder": "transformer",
        }


_register_qwenimage21_single_file()

BASE_MODEL = "Qwen/Qwen-Image-2.1"
DEFAULT_GGUF = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "models",
    "qwen_image_2.1_Q4_K_S.gguf",
)
DEFAULT_FILENAME = "/tmp/ircawp_generated/qwenimage21.png"
DEFAULT_ASPECT = 1.5
DEFAULT_MAX_OUTPUT_SIZE = 1024
DEFAULT_STEPS = 40
REMASTER_EXTRA_STEPS = 4

DEFAULT_CFG = 2.0


class qwenimage21(MediaBackend):
    def __init__(self, backend_config: dict = {}):
        super().__init__(backend_config)

        gguf_path = self.backend_config.get("gguf", DEFAULT_GGUF)
        text_encoder_4bit = self.backend_config.get("text_encoder_4bit", True)
        # Base model repo (text encoder + VAE + tokenizer). Can be a local
        # directory for offline servers — see docs/QWENIMAGE21.md.
        base_model = self.backend_config.get("base_model", BASE_MODEL)

        # from_single_file requires a valid URL (or local file path). Normalize
        # a bare "repo_id/file.gguf" into a full HuggingFace resolve URL.
        if not gguf_path.startswith(
            ("http://", "https://", "hf.co", "huggingface.co")
        ) and not os.path.isfile(gguf_path):
            repo_id, _, filename = gguf_path.rpartition("/")
            gguf_path = f"https://huggingface.co/{repo_id}/blob/main/{filename}"

        # Load GGUF-quantized transformer
        from diffusers import QwenImage21Transformer2DModel

        transformer = QwenImage21Transformer2DModel.from_single_file(
            gguf_path,
            quantization_config=GGUFQuantizationConfig(compute_dtype=torch.bfloat16),
            config=base_model,
            subfolder="transformer",
        )

        # Build pipeline — text encoder + VAE from base repo
        pipe_kwargs = {
            "transformer": transformer,
            "torch_dtype": torch.bfloat16,
        }
        if text_encoder_4bit:
            from diffusers.quantizers import PipelineQuantizationConfig

            # The text encoder is a transformers model, so it needs
            # transformers' BitsAndBytesConfig (NOT diffusers' — they are
            # distinct classes and transformers' AutoHfQuantizer rejects the
            # diffusers one).
            from transformers.utils.quantization_config import BitsAndBytesConfig

            pipe_kwargs["quantization_config"] = PipelineQuantizationConfig(
                quant_mapping={
                    "text_encoder": BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.bfloat16,
                    )
                }
            )

        self.pipe = QwenImage21Pipeline.from_pretrained(base_model, **pipe_kwargs)
        self.pipe.enable_model_cpu_offload()
        # VAE decode of a full-res latent in one pass spikes memory after the last
        # step; tiling keeps that final decode within budget.
        # NOTE: This is commented out because it causes strange visual artifacts.
        # self.pipe.vae.enable_tiling()

    def _parse_aspect(self, config: dict) -> float:
        """Parse aspect ratio from config."""
        aspect = config.get("aspect", DEFAULT_ASPECT)
        if isinstance(aspect, str):
            if ":" in aspect:
                parts = aspect.split(":")
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    return float(parts[0]) / float(parts[1])
            try:
                return float(aspect)
            except ValueError:
                pass
        return float(aspect) if isinstance(aspect, (int, float)) else DEFAULT_ASPECT

    def execute(
        self,
        prompt: str,
        config: dict = {},
        batch_id=None,
        media=[],
    ) -> tuple[str, str]:
        steps = config.get("steps", DEFAULT_STEPS)
        has_image = len(media) > 0

        # Output path
        if batch_id is not None:
            output_file = f"/tmp/ircawp_generated/qwenimage21.{batch_id}.png"
        else:
            output_file = config.get("output_file", DEFAULT_FILENAME)

        scale_result = config.get("scale", 1.0)
        do_remaster = config.get("remaster", False)

        seed = config.get("seed")
        if seed is None:
            seed = torch.randint(0, 1000000, (1,)).item()
        max_output_size = config.get("max_output_size", DEFAULT_MAX_OUTPUT_SIZE)

        # Compute dimensions
        # Explicit width/height from config (e.g. --aspect) always take priority
        if "width" in config and "height" in config:
            width = config["width"]
            height = config["height"]
        elif not has_image:
            aspect = self._parse_aspect(config)

            if aspect >= 1.0:
                width = max_output_size
                height = int(max_output_size / aspect)
            else:
                width = int(max_output_size * aspect)
                height = max_output_size

            # Ensure dimensions are divisible by 16
            width = round(width / 16) * 16
            height = round(height / 16) * 16
        else:
            # Dimensions will be set from input image below
            width, height = max_output_size, int(max_output_size / DEFAULT_ASPECT)

        prompt = prompt.strip()
        final_prompt = prompt

        if do_remaster:
            final_prompt = (
                """Enhance this image while faithfully preserving its original style, medium, composition, colors, and subject. Increase sharpness, clarity, and fine detail. Remove blur, noise, grain, compression artifacts, and haze. Restore crisp edges and clean lines. Keep the existing art style exactly as it is — do not change the medium, do not add photorealism, do not alter the pose, anatomy, proportions, or any text. The result should look like a cleaner, higher-fidelity version of the same image.. {}"""
            ).format(final_prompt)
            steps += REMASTER_EXTRA_STEPS

        # Load input media
        media_pil = []
        if has_image:
            for image_path in media:
                media_pil.append(load_image(image_path))

            if media_pil[0] is not None:
                # Only derive dimensions from input image if config didn't specify them
                if "width" not in config or "height" not in config:
                    longest_side = max(media_pil[0].width, media_pil[0].height)
                    if longest_side < max_output_size:
                        scale_result = max_output_size / longest_side
                    elif longest_side > max_output_size:
                        scale_result = max_output_size / longest_side

                    width = int(media_pil[0].width * scale_result)
                    height = int(media_pil[0].height * scale_result)
                aspect = width / height
            else:
                aspect = DEFAULT_ASPECT
        else:
            aspect = self._parse_aspect(config)

        # Generate
        pipeline_kwargs = {
            "prompt": final_prompt,
            "width": width,
            "height": height,
            "num_inference_steps": steps,
            "generator": torch.Generator("cpu").manual_seed(seed),
            "image": media_pil if has_image else None,
            "callback_on_step_end": self.cancellation_callback(config),
        }
        true_cfg_scale = config.get("true_cfg_scale")
        if true_cfg_scale is not None:
            pipeline_kwargs["negative_prompt"] = ""
            pipeline_kwargs["true_cfg_scale"] = true_cfg_scale

        output_image = self.pipe(
            **pipeline_kwargs,
        ).images[0]

        self._save_image_with_metadata(
            output_image,
            output_file,
            final_prompt,
            seed=seed,
            model="qwenimage21",
            inference_steps=steps,
            width=width,
            height=height,
            aspect_ratio=str(aspect),
        )

        self.last_imagegen_prompt = final_prompt.strip()
        return output_file, final_prompt

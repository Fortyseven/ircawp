"""FLUX.2 Klein backend for media-server.

Prompt refinement is handled by the client (ircawp bot).
This backend receives a final, ready-to-use prompt.
"""

from .MediaBackend import MediaBackend

import torch
from diffusers import Flux2KleinPipeline
from diffusers.utils import load_image


DEFAULT_FILENAME = "/tmp/ircawp_generated/flux2klein.png"
DEFAULT_ASPECT = 1.5
DEFAULT_MAX_OUTPUT_SIZE = 1024

INF_STEPS = 5
CFG_SCALE = 4


class flux2klein(MediaBackend):
    def __init__(self, backend_config: dict = {}):
        super().__init__(backend_config)
        self.pipe = Flux2KleinPipeline.from_pretrained(
            "black-forest-labs/FLUX.2-klein-4B",
            torch_dtype=torch.bfloat16,
        )
        self.pipe.to("cpu")
        self.pipe.enable_model_cpu_offload()

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
        steps = config.get("steps", INF_STEPS)
        has_image = len(media) > 0

        # Output path
        if batch_id is not None:
            output_file = f"/tmp/ircawp_generated/flux2klein.{batch_id}.png"
        else:
            output_file = config.get("output_file", DEFAULT_FILENAME)

        scale_result = config.get("scale", 1.0)
        do_remaster = config.get("remaster", False)

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
            steps += 3

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
        output_image = self.pipe(
            prompt=final_prompt,
            width=width,
            height=height,
            num_inference_steps=steps,
            guidance_scale=CFG_SCALE,
            generator=torch.Generator("cpu").manual_seed(seed),
            image=media_pil if has_image else None,
            callback_on_step_end=self.cancellation_callback(config),
        ).images[0]

        self._save_image_with_metadata(
            output_image,
            output_file,
            final_prompt,
            seed=seed,
            model="flux2klein",
            guidance_scale=CFG_SCALE,
            inference_steps=steps,
            width=width,
            height=height,
            aspect_ratio=str(aspect),
        )

        self.last_imagegen_prompt = final_prompt.strip()
        return output_file, final_prompt

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
    def __init__(self):
        super().__init__()
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
        steps = INF_STEPS
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
        if not has_image:
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
                """Transform this image into a modern, cinematic masterpiece as if shot with a professional DSLR camera with a 50mm f/1.4 lens. A sharp, natural, and highly detailed photo. Deblur the entire image, completely remove film grain and digital noise, and restore clarity without altering composition, aspect ratio, or subject structure. Make no changes to pose, anatomy, or typography. Remove haze, dirt, and atmospheric distortion, then enhance dynamic range while maintaining original color tones.
Specifically target and recover overexposed, blown-out areas using intelligent tone mapping and localized HDR reconstruction, preserve detail in highlights without crushing midtones or shadows. Convert harsh or flat lighting into soft, cinematic lighting with natural falloff and depth. Replace all digital artifacts with ultra-high-fidelity textures, skin, fabric, and fur, matching real-world material properties. Perform professional, balanced natural color correction. Upscale to sharp 4K resolution, resimulate the image as if captured by a professional photographer with precise focus, depth, and lighting control.
Final output: a photorealistic, high dynamic range (HDR), cinema-quality photograph. A photo that is sharp, clean, and rich in detail, with every element rendered with professional photographic precision. Recovered highlights retain texture and form, avoiding flat white or clipped pixels. A photo achieving a balanced, visually compelling image with full tonal fidelity. Preserve text details. Preserve facial structure. {}"""
            ).format(final_prompt)
            steps = 8

        # Load input media
        media_pil = []
        if has_image:
            for image_path in media:
                media_pil.append(load_image(image_path))

            if media_pil[0] is not None:
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

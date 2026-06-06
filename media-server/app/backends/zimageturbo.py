"""Z-Image Turbo backend for media-server.

Prompt refinement is handled by the client (ircawp bot).
This backend receives a final, ready-to-use prompt.
"""

from .MediaBackend import MediaBackend

import torch
from diffusers import ZImagePipeline


DEFAULT_FILENAME = "/tmp/ircawp_generated/zimageturbo.png"
DEFAULT_ASPECT = 1.5
MAX_WIDTH_HEIGHT = 1280

INF_STEPS = 9
CFG_SCALE = 0.0
MODEL = "Tongyi-MAI/Z-Image-Turbo"


class zimageturbo(MediaBackend):
    def __init__(self):
        super().__init__()
        self.pipe = ZImagePipeline.from_pretrained(
            MODEL,
            torch_dtype=torch.bfloat16,
            low_cpu_mem_usage=True,
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
        if batch_id is not None:
            output_file = f"/tmp/ircawp_generated/zimageturbo.{batch_id}.png"
        else:
            output_file = config.get("output_file", DEFAULT_FILENAME)

        seed = torch.randint(0, 1000000, (1,)).item()

        aspect = self._parse_aspect(config)

        if isinstance(aspect, float):
            if aspect >= 1.0:
                width = MAX_WIDTH_HEIGHT
                height = int(MAX_WIDTH_HEIGHT / aspect)
            else:
                width = int(MAX_WIDTH_HEIGHT * aspect)
                height = MAX_WIDTH_HEIGHT
        else:
            width = MAX_WIDTH_HEIGHT
            height = int(MAX_WIDTH_HEIGHT / DEFAULT_ASPECT)

        # Ensure dimensions are divisible by 16
        width = round(width / 16) * 16
        height = round(height / 16) * 16

        prompt = prompt.strip()
        final_prompt = prompt

        image = self.pipe(
            prompt=final_prompt,
            width=width,
            height=height,
            num_inference_steps=INF_STEPS,
            guidance_scale=CFG_SCALE,
            generator=torch.Generator("cpu").manual_seed(seed),
        ).images[0]

        self._save_image_with_metadata(
            image,
            output_file,
            final_prompt,
            seed=seed,
            model="zimageturbo",
            guidance_scale=CFG_SCALE,
            inference_steps=INF_STEPS,
            width=width,
            height=height,
            aspect_ratio=str(aspect),
        )

        self.last_imagegen_prompt = final_prompt.strip()
        return output_file, final_prompt

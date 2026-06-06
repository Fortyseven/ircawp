"""SDXS backend for media-server."""

from .MediaBackend import MediaBackend

import torch
import random

from diffusers import StableDiffusionPipeline


DEFAULT_FILENAME = "/tmp/ircawp_generated/sdxs.png"


class sdxs(MediaBackend):
    def __init__(self):
        super().__init__()

        self.repo = "IDKiro/sdxs-512-dreamshaper"
        self.pipe = StableDiffusionPipeline.from_pretrained(
            self.repo,
            torch_dtype=torch.float32,
            safety_checker=None,
        )
        self.pipe.to("cpu")

    def execute(
        self,
        prompt: str,
        config: dict = {},
        batch_id=None,
        media=[],
    ) -> tuple[str, str]:
        if batch_id is not None:
            output_file = f"/tmp/ircawp_generated/sdxs.{batch_id}.png"
        else:
            output_file = config.get("output_file", DEFAULT_FILENAME)

        seed = random.randint(0, 100000)
        image = self.pipe(
            prompt=prompt,
            num_inference_steps=1,
            guidance_scale=0.5,
            generator=torch.Generator(device="cpu").manual_seed(seed),
            safety_checker=None,
        ).images[0]

        self._save_image_with_metadata(
            image,
            output_file,
            prompt,
            seed=seed,
            model="sdxs",
            guidance_scale=0.5,
            inference_steps=1,
            width=image.width,
            height=image.height,
        )

        return output_file, prompt

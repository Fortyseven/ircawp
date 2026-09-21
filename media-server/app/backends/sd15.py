"""Stable Diffusion 1.5 backend for media-server."""

from .MediaBackend import MediaBackend

import torch
import random

torch.backends.cudnn.enabled = False

from diffusers import StableDiffusionPipeline, EulerAncestralDiscreteScheduler  # noqa: E402


DEFAULT_FILENAME = "/tmp/ircawp_generated/sd15.png"


class sd15(MediaBackend):
    def __init__(self, backend_config: dict = {}):
        super().__init__(backend_config)
        self.repo = "/models/stable-diffusion/custom/2023-04/526mixV15_v15.safetensors"
        self.pipe = StableDiffusionPipeline.from_single_file(
            self.repo, revision="fp16", torch_dtype=torch.float16
        )
        self.pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(
            self.pipe.scheduler.config
        )
        self.pipe.to("cuda")

    def execute(
        self,
        prompt: str,
        config: dict = {},
        batch_id=None,
        media=[],
    ) -> tuple[str, str]:
        if batch_id is not None:
            output_file = f"/tmp/ircawp_generated/sd15.{batch_id}.png"
        else:
            output_file = config.get("output_file", DEFAULT_FILENAME)

        seed = random.randint(0, 100000)
        steps = config.get("steps", 25)
        image = self.pipe(
            prompt=prompt,
            num_inference_steps=steps,
            guidance_scale=7,
            generator=torch.Generator("cuda").manual_seed(seed),
        ).images[0]

        self._save_image_with_metadata(
            image,
            output_file,
            prompt,
            seed=seed,
            model="sd15",
            guidance_scale=7,
            inference_steps=steps,
            width=image.width,
            height=image.height,
        )

        return output_file, prompt

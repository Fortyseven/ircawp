"""Hyper SDXL backend for media-server."""

from .MediaBackend import MediaBackend

import torch
import random

from diffusers import DiffusionPipeline, UNet2DConditionModel, LCMScheduler
from safetensors.torch import load_file


BASE_MODEL_ID = "stabilityai/stable-diffusion-xl-base-1.0"
DEFAULT_FILENAME = "/tmp/ircawp_generated/hypersdxl.png"
CKPT_LOCAL_PATH = "/models/Hyper-SDXL-1step-Unet.safetensors"
DEVICE = "cuda"


class hyper_sdxl(MediaBackend):
    def __init__(self):
        super().__init__()

        unet = UNet2DConditionModel.from_config(
            BASE_MODEL_ID,
            subfolder="unet",
        ).to(DEVICE)

        unet.load_state_dict(load_file(CKPT_LOCAL_PATH, device=DEVICE))

        self.pipe = DiffusionPipeline.from_pretrained(
            BASE_MODEL_ID,
            unet=unet,
            variant="fp16",
        ).to(DEVICE)

        self.pipe.scheduler = LCMScheduler.from_config(self.pipe.scheduler.config)

    def execute(
        self,
        prompt: str,
        config: dict = {},
        batch_id=None,
        media=[],
    ) -> tuple[str, str]:
        if batch_id is not None:
            output_file = f"/tmp/ircawp_generated/hypersdxl.{batch_id}.png"
        else:
            output_file = config.get("output_file", DEFAULT_FILENAME)

        seed = random.randint(0, 100000)

        image = self.pipe(
            prompt=prompt,
            num_inference_steps=1,
            guidance_scale=0,
            seed=seed,
            timesteps=[800],
            generator=torch.Generator(device=DEVICE).manual_seed(seed),
        ).images[0]

        self._save_image_with_metadata(
            image,
            output_file,
            prompt,
            seed=seed,
            model="hyper_sdxl",
            guidance_scale=0,
            inference_steps=1,
            width=image.width,
            height=image.height,
        )

        return output_file, prompt

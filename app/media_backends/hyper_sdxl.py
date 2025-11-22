if __name__ == "__main__":
    import sys

    print("Running as script")
    sys.path.append(".")

import torch
import random

from .MediaBackend import MediaBackend
from diffusers import DiffusionPipeline, UNet2DConditionModel, LCMScheduler
from safetensors.torch import load_file

BASE_MODEL_ID = "stabilityai/stable-diffusion-xl-base-1.0"

DEFAULT_FILENAME = "/tmp/ircawp.hypersdxl.png"
CKPT_LOCAL_PATH = "/models/Hyper-SDXL-1step-Unet.safetensors"

DEVICE = "cpu"


class hyper_sdxl(MediaBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Load model.
        unet = UNet2DConditionModel.from_config(
            BASE_MODEL_ID,
            subfolder="unet",  # type: ignore
        ).to(DEVICE)

        unet.load_state_dict(load_file(CKPT_LOCAL_PATH, device=DEVICE))

        self.pipe = DiffusionPipeline.from_pretrained(
            BASE_MODEL_ID,
            unet=unet,
            variant="fp16",
        ).to(DEVICE)

        # Use LCM scheduler instead of ddim scheduler to support specific timestep number inputs
        self.pipe.scheduler = LCMScheduler.from_config(self.pipe.scheduler.config)

    def execute(self, prompt: str, output_file: str = DEFAULT_FILENAME) -> str:
        print(f"HyperSDXL: Prompt: {prompt}")
        seed = random.randint(0, 100000)

        image = self.pipe(
            prompt=prompt,
            num_inference_steps=1,
            guidance_scale=0,
            seed=seed,
            timesteps=[800],
            generator=torch.Generator(device=DEVICE).manual_seed(seed),
        ).images[0]

        print(f"HyperSDXL saving to {output_file}")

        image.save(output_file)

        print("HyperSDXL done")

        return output_file


if __name__ == "__main__":
    backend = HyperSDXL(None)
    backend.execute("A fat cat in a field of flowers")

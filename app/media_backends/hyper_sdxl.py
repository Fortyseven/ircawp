import torch
import time
import random

from .__MediaBackend import MediaBackend
from diffusers import DiffusionPipeline, UNet2DConditionModel, LCMScheduler
from safetensors.torch import load_file

BASE_MODEL_ID = "stabilityai/stable-diffusion-xl-base-1.0"

DEFAULT_FILENAME = "/tmp/ircawp.hypersdxl.png"
CKPT_LOCAL_PATH = "/models/stable-diffusion/Hyper-SDXL-1step-Unet.safetensors"


class HyperSDXL(MediaBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Load model.
        unet = UNet2DConditionModel.from_config(
            BASE_MODEL_ID, subfolder="unet"
        ).to("cuda", torch.float16)

        # unet.load_state_dict(load_file(hf_hub_download(repo_name, ckpt_name), device="cuda"))
        unet.load_state_dict(load_file(CKPT_LOCAL_PATH, device="cuda"))

        self.pipe = DiffusionPipeline.from_pretrained(
            BASE_MODEL_ID, unet=unet, torch_dtype=torch.float16, variant="fp16"
        ).to("cuda")

        # Use LCM scheduler instead of ddim scheduler to support specific timestep number inputs
        self.pipe.scheduler = LCMScheduler.from_config(
            self.pipe.scheduler.config
        )

    def execute(self, prompt: str, output_file: str = DEFAULT_FILENAME) -> str:
        print(f"HyperSDXL: Prompt: {prompt}")
        seed = random.randint(0, 100000)

        image = self.pipe(
            prompt=prompt,
            num_inference_steps=1,
            guidance_scale=0,
            timesteps=[800],
            generator=torch.Generator(device="cpu").manual_seed(seed),
        ).images[0]

        image.save(output_file)

        return output_file

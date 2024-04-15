import torch
import time
import random

from .BaseImageGen import BaseImageGen
from diffusers import StableDiffusionPipeline, AutoencoderKL

DEFAULT_FILENAME = "/tmp/ircawp.sdxs.png"


class SDXS(BaseImageGen):
    def __init__(self):
        self.repo = "IDKiro/sdxs-512-dreamshaper"
        self.weight_type = torch.float32
        self.pipe = StableDiffusionPipeline.from_pretrained(
            self.repo,
            torch_dtype=self.weight_type,
            safety_checker=None,
        )
        self.pipe.to("cpu")

    def generateImage(self, prompt: str, output_file: str = DEFAULT_FILENAME):
        seed = random.randint(0, 100000)
        image = self.pipe(
            prompt,
            num_inference_steps=1,
            guidance_scale=0,
            generator=torch.Generator(device="cpu").manual_seed(seed),
            safety_checker=None,
            quiet=True,
        ).images[0]

        image.save(output_file)

import torch
import random

torch.backends.cudnn.enabled = False

from .MediaBackend import MediaBackend  # noqa: E402
from diffusers import StableDiffusionPipeline, EulerAncestralDiscreteScheduler  # noqa: E402

DEFAULT_FILENAME = "/tmp/ircawp.sd15.png"


class sd15(MediaBackend):
    def __init__(self):
        # self.repo = "/models/526mixV15_v15.safetensors"
        # self.repo = "/models/level4_v50BakedVAEFp16.safetensors"
        self.repo = "/models/stable-diffusion/custom/2023-04/526mixV15_v15.safetensors"
        self.pipe = StableDiffusionPipeline.from_single_file(
            self.repo, revision="fp16", torch_dtype=torch.float16
        )
        self.pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(
            self.pipe.scheduler.config
        )
        self.pipe.to("cuda")

    def generateImage(self, prompt: str, output_file: str = DEFAULT_FILENAME):
        seed = random.randint(0, 100000)
        image = self.pipe(
            prompt=prompt,
            num_inference_steps=25,
            guidance_scale=7,
            generator=torch.Generator("cuda").manual_seed(seed),
        ).images[0]
        image.save(output_file)

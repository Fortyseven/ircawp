import torch
import random

from .MediaBackend import MediaBackend
from diffusers import StableDiffusionPipeline

DEFAULT_FILENAME = "/tmp/ircawp.sdxs.png"


class sdxs(MediaBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.repo = "IDKiro/sdxs-512-dreamshaper"
        self.weight_type = torch.float32
        self.pipe = StableDiffusionPipeline.from_pretrained(
            self.repo,
            torch_dtype=self.weight_type,
            safety_checker=None,
        )
        self.pipe.to("cpu")

    def execute(self, prompt: str, output_file: str = DEFAULT_FILENAME) -> str:
        print(f"[yellow]SDXS prompt: {prompt}[/yellow]")
        seed = random.randint(0, 100000)
        image = self.pipe(
            prompt=prompt,
            num_inference_steps=1,
            guidance_scale=0.5,
            generator=torch.Generator(device="cpu").manual_seed(seed),
            safety_checker=None,
        ).images[0]

        image.save(output_file)

        return output_file

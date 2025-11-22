if __name__ == "__main__":
    import sys

    print("Running as script")
    sys.path.append(".")
    from MediaBackend import MediaBackend

else:
    from .MediaBackend import MediaBackend

import torch
import random

from diffusers import StableDiffusionPipeline

DEFAULT_FILENAME = "/tmp/ircawp.sdxs.png"


class sdxs(MediaBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.repo = "IDKiro/sdxs-512-dreamshaper"
        self.pipe = StableDiffusionPipeline.from_pretrained(
            self.repo,
            torch_dtype=torch.float32,
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

        print(f"[green]SDXS wrote:[/green] {output_file}")

        return output_file


if __name__ == "__main__":
    backend = sdxs(None)
    saved_to = backend.execute("A beautiful landscape with mountains and a river")
    print(f"Image saved to {saved_to}")

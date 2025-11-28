if __name__ == "__main__":
    import sys

    print("Running as script")
    sys.path.append(".")
    from MediaBackend import MediaBackend

else:
    from .MediaBackend import MediaBackend

import torch
from diffusers import ZImagePipeline

DEFAULT_FILENAME = "/tmp/ircawp.zimageturbo.png"

MODEL = "Tongyi-MAI/Z-Image-Turbo"


class zimageturbo(MediaBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        torch.cuda.empty_cache()
        self.pipe = ZImagePipeline.from_pretrained(
            MODEL,
            torch_dtype=torch.bfloat16,
            low_cpu_mem_usage=False,
        )
        # self.pipe.to("cuda")
        self.pipe.enable_model_cpu_offload()

    def execute(self, prompt: str, output_file: str = DEFAULT_FILENAME) -> str:
        seed = torch.randint(0, 1000000, (1,)).item()
        image = self.pipe(
            prompt=prompt,
            width=1248,
            height=832,
            num_inference_steps=9,  # This actually results in 8 DiT forwards
            guidance_scale=0.0,  # Guidance should be 0 for the Turbo models
            generator=torch.Generator("cpu").manual_seed(seed),
        ).images[0]

        image.save(output_file)

        return output_file


if __name__ == "__main__":
    backend = zimageturbo(None)

    saved_to = backend.execute("A beautiful landscape with mountains and a river")
    print(f"Image saved to {saved_to}")

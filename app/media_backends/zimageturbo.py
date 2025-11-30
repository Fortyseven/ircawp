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
# LORA_PATH = "app/media_backends/zimage-lora/technically-color.safetensors"

DEFAULT_WIDTH = 1440  # 1056
DEFAULT_HEIGHT = 960  # 704
INF_STEPS = 9
CFG_SCALE = 0.0

MODEL = "Tongyi-MAI/Z-Image-Turbo"


class zimageturbo(MediaBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pipe = ZImagePipeline.from_pretrained(
            MODEL,
            torch_dtype=torch.bfloat16,
            low_cpu_mem_usage=True,
        )

        self.pipe.to("cpu")
        self.pipe.enable_model_cpu_offload()

    def execute(self, prompt: str, output_file: str = DEFAULT_FILENAME) -> str:
        torch.cuda.empty_cache()
        seed = torch.randint(0, 1000000, (1,)).item()
        image = self.pipe(
            prompt=prompt,
            width=DEFAULT_WIDTH,
            height=DEFAULT_HEIGHT,
            num_inference_steps=INF_STEPS,  # This actually results in 8 DiT forwards
            guidance_scale=CFG_SCALE,  # Guidance should be 0 for the Turbo models
            generator=torch.Generator("cpu").manual_seed(seed),
        ).images[0]

        image.save(output_file)

        return output_file


if __name__ == "__main__":
    backend = zimageturbo(None)

    # saved_to = backend.execute("A beautiful landscape with mountains and a river")
    saved_to = backend.execute(
        "A violent nightmare clown covered in blood; children running in terror."
    )
    print(f"Image saved to {saved_to}")

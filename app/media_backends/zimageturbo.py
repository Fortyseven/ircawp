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

# DEFAULT_WIDTH = 1440  # 1056
# DEFAULT_HEIGHT = 960  # 704
DEFAULT_ASPECT = 1.5
MAX_WIDTH_HEIGHT = 1440

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

    def execute(self, prompt: str, config: dict) -> str:
        output_file = config.get("output_file", DEFAULT_FILENAME)
        torch.cuda.empty_cache()
        seed = torch.randint(0, 1000000, (1,)).item()
        # self.pipe.unet.load_attn_procs(LORA_PATH, weight=0.75)

        aspect = config.get("aspect", DEFAULT_ASPECT)

        # check for common ratio strings ("16:9", etc), or take float directly
        if "aspect" in config:
            ratio_str = config["aspect"]
            if ":" in ratio_str:
                parts = ratio_str.split(":")
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    aspect = float(parts[0]) / float(parts[1])
            else:
                try:
                    aspect = float(ratio_str)
                except ValueError:
                    pass  # keep default if conversion fails

        if type(aspect) is float:
            if aspect >= 1.0:
                width = MAX_WIDTH_HEIGHT
                height = int(MAX_WIDTH_HEIGHT / aspect)
            else:
                width = int(MAX_WIDTH_HEIGHT * aspect)
                height = MAX_WIDTH_HEIGHT
        else:
            width = MAX_WIDTH_HEIGHT
            height = int(MAX_WIDTH_HEIGHT / DEFAULT_ASPECT)
            print("Invalid aspect ratio provided, using default.")

        # Ensure dimensions are divisible by 16
        width = round(width / 16) * 16
        height = round(height / 16) * 16

        self.pipe.set_progress_bar_config(disable=True)

        print("Generating size:", width, "x", height, "seed:", seed, "aspect:", aspect)

        image = self.pipe(
            prompt=prompt,
            width=width,
            height=height,
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

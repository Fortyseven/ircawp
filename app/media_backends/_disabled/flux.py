# NOTE: I am so fucking tired of toiling with this absolute bullshit.


if __name__ == "__main__":
    import sys

    print("Running as script")
    sys.path.append(".")

import os
import torch

# from diffusers import DiffusionPipeline
from diffusers import FluxTransformer2DModel, FluxPipeline

MODEL_PATH = "/models/flux/flux1-schnell-bnb-nf4.safetensors"


class FluxSchnell:
    """A class for managing and running the FLUX.1-schnell model"""

    # repo_id = "black-forest-labs/FLUX.1-schnell"
    # repo_id = "argmaxinc/mlx-FLUX.1-schnell-4bit-quantized"
    # repo_id = "dhairyashil/FLUX.1-schnell-mflux-4bit"
    # repo_id = "sayakpaul/flux.1-schnell-nf4-pkg"
    # repo_id = "AITRADER/MFLUX.1-schnell-4-bit"
    repo_id = "gradjitta/flux.1-schnell-nf4"

    def __init__(
        self,
        device: str = None,
        create_dirs: bool = True,
        enable_sequential_cpu_offload: bool = True,
    ):
        self.device = self.initialize_device(device)

        config = FluxTransformer2DModel.load_config(
            # "black-forest-labs/flux.1-schnell", subfolder="transformer"
            self.repo_id
        )
        self.model: FluxTransformer2DModel = FluxTransformer2DModel.from_config(
            config
        ).to("cpu")  # .to(torch.bfloat16)

        self.pipeline = FluxPipeline.from_pretrained(
            self.repo_id,
            # text_encoder_2=text_encoder_8bit,
            transformer=self.model,
            torch_dtype=torch.float16,
            device_map="balanced",
        )

    def generate(self, prompt, num_inference_steps=4, save=True):
        """Returns list of generated images for given prompts"""
        images = self.pipeline(prompt).images
        for i, image in enumerate(images):
            if save:
                image.save(
                    f"temp_{i}.png"
                    # os.path.join(
                    #     self.module_dir, "generated-images", f"generated_image_{i}.png"
                    # )
                )
        return images

    # def instantiate_model(self, repo_id, device, dtype, enable_sequential_cpu_offload):
    #     """Returns instantiated model"""
    #     # model = DiffusionPipeline.from_pretrained(repo_id, torch_dtype=dtype)
    #     model = FluxTransformer2DModel.from_pretrained(
    #         repo_id,
    #         # subfolder="transformer",
    #         torch_dtype=dtype,
    #     )
    #     if enable_sequential_cpu_offload:
    #         model.enable_sequential_cpu_offload(device=device)
    #     else:
    #         model = model.to(device)
    #     return model

    def initialize_device(self, device: str):
        """Return the GPU device based on availability"""
        if device is None:
            if torch.cuda.is_available():
                device = "cuda"
            elif torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"
        return torch.device(device)

    # def create_dirs(self, root):
    #     """Creates required directories under given root directory"""
    #     dir_names = ["generated-images"]
    #     for dir_name in dir_names:
    #         os.makedirs(os.path.join(root, dir_name), exist_ok=True)


if __name__ == "__main__":
    prompt = "A cat holding a sign that says hello world"
    flux_schnell = FluxSchnell().generate(prompt, 4)

# if __name__ == "__main__":
#     backend = Flux(None)
#     backend.execute("A cat in a field of flowers")

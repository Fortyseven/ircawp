if __name__ == "__main__":
    import sys

    print("Running as script")
    sys.path.append(".")

import torch
import time
import random
import os

import torch

from app.media_backends.__MediaBackend import MediaBackend

from optimum.quanto import freeze, qfloat8, quantize

from diffusers import FlowMatchEulerDiscreteScheduler, AutoencoderKL
from diffusers.models.transformers.transformer_flux import (
    FluxTransformer2DModel,
)
from diffusers.pipelines.flux.pipeline_flux import FluxPipeline
from transformers import (
    CLIPTextModel,
    CLIPTokenizer,
    T5EncoderModel,
    T5TokenizerFast,
)

# BASE_MODEL_ID = "stabilityai/stable-diffusion-xl-base-1.0"

DEFAULT_FILENAME = "/tmp/ircawp.flux.png"
# CKPT_LOCAL_PATH = "/models/stable-diffusion/Hyper-SDXL-1step-Unet.safetensors"
# MODEL_PATH = "/models/flux/flux1-schnell-fp8.safetensors"
MODEL_PATH = "https://huggingface.co/Kijai/flux-fp8/blob/main/flux1-dev-fp8.safetensors"
# MODEL_PATH = "/models/flux/flux1-schnell-bnb-nf4.safetensors"
# MODEL_PATH = "/models/flux/gguf/schnell/flux1-schnell-Q2_K.gguf"

revision = "refs/pr/1"
dtype = torch.bfloat16


class Flux(MediaBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        from diffusers import FluxPipeline, FluxTransformer2DModel

        # transformer = FluxTransformer2DModel.from_single_file(MODEL_PATH)
        # quantize(transformer, weights=qfloat8)
        # freeze(transformer)

        # bfl_repo = "black-forest-labs/FLUX.1-dev"

        # text_encoder_2 = T5EncoderModel.from_pretrained(
        #     bfl_repo, subfolder="text_encoder_2", torch_dtype=dtype
        # )
        # quantize(text_encoder_2, weights=qfloat8)
        # freeze(text_encoder_2)

        pipe = FluxPipeline.from_pretrained(
            "flux-fp8/flux1-dev-fp8.safetensors",
            transformer=None,
            text_encoder_2=None,
            torch_dtype=dtype,
        )
        # pipe.transformer = transformer
        # pipe.text_encoder_2 = text_encoder_2

        pipe.enable_model_cpu_offload()

        self.pipe = pipe

        print("[red]Flux initialized?????[/red]")

        # self.pipe = FluxPipeline.from_pretrained(
        #     MODEL_PATH, transformer=transformer
        # )

        # self.pipe.to("cuda")

        # self.scheduler = FlowMatchEulerDiscreteScheduler.from_pretrained(
        #     MODEL_PATH, subfolder="scheduler", revision=revision
        # )
        # self.text_encoder = CLIPTextModel.from_pretrained(
        #     "openai/clip-vit-large-patch14", torch_dtype=dtype
        # )
        # self.tokenizer = CLIPTokenizer.from_pretrained(
        #     "openai/clip-vit-large-patch14", torch_dtype=dtype
        # )
        # self.text_encoder_2 = T5EncoderModel.from_pretrained(
        #     MODEL_PATH,
        #     subfolder="text_encoder_2",
        #     torch_dtype=dtype,
        #     revision=revision,
        # )
        # self.tokenizer_2 = T5TokenizerFast.from_pretrained(
        #     MODEL_PATH,
        #     subfolder="tokenizer_2",
        #     torch_dtype=dtype,
        #     revision=revision,
        # )
        # self.vae = AutoencoderKL.from_pretrained(
        #     MODEL_PATH, subfolder="vae", torch_dtype=dtype, revision=revision
        # )
        # self.transformer = FluxTransformer2DModel.from_pretrained(
        #     MODEL_PATH,
        #     subfolder="transformer",
        #     torch_dtype=dtype,
        #     revision=revision,
        # )

        # quantize(self.transformer, weights=qfloat8)
        # freeze(self.transformer)

        # quantize(self.text_encoder_2, weights=qfloat8)
        # freeze(self.text_encoder_2)

    def execute(self, prompt: str, output_file: str = DEFAULT_FILENAME) -> str:
        print(f"Flux Prompt: {prompt}")
        seed = random.randint(0, 100000)

        # image = self.pipe(
        #     prompt=prompt,
        #     num_inference_steps=1,
        #     guidance_scale=0,
        #     # timesteps=[800],
        #     timesteps=[800],
        #     generator=torch.Generator(device="cpu").manual_seed(seed),
        # ).images[0]

        image = self.pipe(
            prompt,
            # height=1024,
            # width=1024,
            guidance_scale=0.0,
            output_type="pil",
            num_inference_steps=4,
            max_sequence_length=256,
            generator=torch.Generator("cpu").manual_seed(seed),
        ).images[0]

        print(f"Flux saving")

        image.save(output_file)

        print(f"Flux done")

        return output_file


if __name__ == "__main__":
    backend = Flux(None)
    backend.execute("A cat in a field of flowers")

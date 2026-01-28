if __name__ == "__main__":
    import sys

    print("Running as script")
    sys.path.append(".")
    from MediaBackend import MediaBackend

else:
    from .MediaBackend import MediaBackend

import torch
from diffusers import Flux2KleinPipeline
from diffusers.utils import load_image
from app.lib.llm_helpers import refinePrompt


DEFAULT_FILENAME = "/tmp/ircawp.flux2klein.png"

DEFAULT_ASPECT = 1.5
MAX_OUT_SIZE = 1280

INF_STEPS = 5
CFG_SCALE = 4


class flux2klein(MediaBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pipe = Flux2KleinPipeline.from_pretrained(
            "black-forest-labs/FLUX.2-klein-4B",
            torch_dtype=torch.bfloat16,
            # low_cpu_mem_usage=True,
        )

        self.pipe.to("cpu")
        self.pipe.enable_model_cpu_offload()

    def execute(
        self, prompt: str, config: dict = {}, batch_id=None, media=[], backend=None
    ) -> (str, str):
        steps = INF_STEPS
        has_image = False

        if media:
            has_image = True

        if batch_id is not None:
            output_file = f"/tmp/ircawp.flux2klein.{batch_id}.png"
        else:
            output_file = config.get("output_file", DEFAULT_FILENAME)

        skip_refinement = config.get("skip_refinement", False)
        scale_result = config.get("scale", 1.0)
        do_remaster = config.get("remaster", False)

        # torch.cuda.empty_cache()

        seed = torch.randint(0, 1000000, (1,)).item()

        # We'll be using the source image size if an image is provided

        if not has_image:
            aspect = config.get("aspect", DEFAULT_ASPECT)

            # check for common ratio strings ("16:9", etc), or take float directly
            if "aspect" in config:
                ratio_value = config["aspect"]
                # If it's already a float, use it directly
                if isinstance(ratio_value, (int, float)):
                    aspect = float(ratio_value)
                else:
                    # It's a string, parse it
                    ratio_str = str(ratio_value)
                    if ":" in ratio_str:
                        parts = ratio_str.split(":")
                        if (
                            len(parts) == 2
                            and parts[0].isdigit()
                            and parts[1].isdigit()
                        ):
                            aspect = float(parts[0]) / float(parts[1])
                    else:
                        try:
                            aspect = float(ratio_str)
                        except ValueError:
                            pass  # keep default if conversion fails

            if type(aspect) is float:
                if aspect >= 1.0:
                    width = MAX_OUT_SIZE
                    height = int(MAX_OUT_SIZE / aspect)
                else:
                    width = int(MAX_OUT_SIZE * aspect)
                    height = MAX_OUT_SIZE
            else:
                width = MAX_OUT_SIZE
                height = int(MAX_OUT_SIZE / DEFAULT_ASPECT)
                print("Invalid aspect ratio provided, using default.")

            # Ensure dimensions are divisible by 16
            width = round(width / 16) * 16
            height = round(height / 16) * 16

            print(
                "Generating size:", width, "x", height, "seed:", seed, "aspect:", aspect
            )

        prompt = prompt.strip()
        final_prompt = prompt

        if do_remaster:
            backend.console.log("[white on blue] remastering input image")

            final_prompt = """Transform this image into a modern, cinematic masterpiece as if shot with a professional DSLR camera with a 50mm f/1.4 lens. A sharp, natural, and highly detailed photo. Deblur the entire image, completely remove film grain and digital noise, and restore clarity without altering composition, aspect ratio, or subject structure. Make no changes to pose, anatomy, or typography. Remove haze, dirt, and atmospheric distortion, then enhance dynamic range while maintaining original color tones.
Specifically target and recover overexposed, blown-out areas using intelligent tone mapping and localized HDR reconstruction, preserve detail in highlights without crushing midtones or shadows. Convert harsh or flat lighting into soft, cinematic lighting with natural falloff and depth. Replace all digital artifacts with ultra-high-fidelity textures, skin, fabric, and fur, matching real-world material properties. Perform professional, balanced natural color correction. Upscale to sharp 4K resolution, resimulate the image as if captured by a professional photographer with precise focus, depth, and lighting control.
Final output: a photorealistic, high dynamic range (HDR), cinema-quality photograph. A photo that is sharp, clean, and rich in detail, with every element rendered with professional photographic precision. Recovered highlights retain texture and form, avoiding flat white or clipped pixels. A photo achieving a balanced, visually compelling image with full tonal fidelity. {}""".format(
                final_prompt
            )
            skip_refinement = True
            steps = 8

        if not skip_refinement:
            refined_prompt = refinePrompt(
                prompt, backend, media, is_edit=len(media) > 0
            )

            final_prompt = refined_prompt.strip()

            if (
                "i'm sorry" in final_prompt.lower()
                or "i cannot" in final_prompt.lower()
            ):
                backend.console.log(
                    "[pink on red] prompt refinement refused, using original"
                )
                final_prompt = prompt.strip()

            backend.console.log(f"[black on green] refined prompt: '{final_prompt}'")

        # --------------------------------------------------------------

        media_pil = []

        if has_image:
            for image_path in media:
                media_pil.append(load_image(image_path))

            # if the image is < 1024px on the longest side, adjust scale_result accordingly so it's at least 1024px on longest side
            if media_pil[0] is not None:
                longest_side = max(media_pil[0].width, media_pil[0].height)
                if longest_side < MAX_OUT_SIZE:
                    print("Adjusting scale_result for small input image!")
                    scale_result = MAX_OUT_SIZE / longest_side
                if longest_side > MAX_OUT_SIZE:
                    print("Adjusting scale_result for large input image!")
                    scale_result = MAX_OUT_SIZE / longest_side

            width = int(media_pil[0].width * scale_result)
            height = int(media_pil[0].height * scale_result)
            aspect = width / height

        # --------------------------------------------------------------

        output_image = self.pipe(
            prompt=final_prompt,
            width=width,
            height=height,
            num_inference_steps=steps,
            guidance_scale=CFG_SCALE,
            generator=torch.Generator("cpu").manual_seed(seed),
            image=media_pil if has_image else None,
        ).images[0]

        self._save_image_with_metadata(
            output_image,
            output_file,
            final_prompt,
            seed=seed,
            model="flux2klein",
            guidance_scale=CFG_SCALE,
            inference_steps=steps,
            width=width,
            height=height,
            aspect_ratio=str(aspect),
        )

        self.last_imagegen_prompt = final_prompt.strip()

        return output_file, final_prompt


if __name__ == "__main__":
    # FIXME
    pass
    # media_backend = flux2klein(None)

    # # saved_to = backend.execute("A beautiful landscape with mountains and a river")
    # saved_to = media_backend.execute(
    #     "A violent nightmare clown covered in blood; children running in terror."
    # )
    # print(f"Image saved to {saved_to}")

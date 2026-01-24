if __name__ == "__main__":
    import sys

    print("Running as script")
    sys.path.append(".")
    from MediaBackend import MediaBackend

else:
    from .MediaBackend import MediaBackend

import torch
from diffusers import Flux2KleinPipeline
from app.lib.llm_helpers import refinePrompt
from PIL import Image
import io
import base64
import requests
import os


DEFAULT_FILENAME = "/tmp/ircawp.flux2klein.png"

DEFAULT_ASPECT = 1.5
MAX_WIDTH_HEIGHT = 1280

INF_STEPS = 6
CFG_SCALE = 4


class flux2klein(MediaBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pipe = Flux2KleinPipeline.from_pretrained(
            "black-forest-labs/FLUX.2-klein-4B",
            torch_dtype=torch.bfloat16,
            low_cpu_mem_usage=True,
        )

        self.pipe.to("cpu")
        self.pipe.enable_model_cpu_offload()

    def _load_image_from_media_item(self, media_item, backend=None):
        """Load a PIL Image from a variety of media_item formats.

        Supported inputs:
        - PIL.Image.Image -> returned as RGB
        - bytes -> interpreted as image bytes
        - base64 data URI or raw base64 string
        - local file path
        - URL (http/https)
        - dict-like with keys: 'path', 'url', 'data', 'content', 'b64', 'bytes'
        """
        if media_item is None:
            return None

        # If it's already a PIL image
        try:
            if isinstance(media_item, Image.Image):
                return media_item.convert("RGB")
        except Exception:
            pass

        # Helper to open bytes
        def _open_bytes(bts):
            try:
                img = Image.open(io.BytesIO(bts))
                return img.convert("RGB")
            except Exception as e:
                if backend and hasattr(backend, "console"):
                    try:
                        backend.console.log(f"[red]Failed to open image bytes: {e}")
                    except Exception:
                        pass
                return None

        # If it's raw bytes
        if isinstance(media_item, (bytes, bytearray)):
            return _open_bytes(bytes(media_item))

        # If it's a dict-like object, try common keys
        if isinstance(media_item, dict):
            # raw bytes
            for key in ("bytes", "image_bytes", "data", "content"):
                if key in media_item and media_item[key] is not None:
                    val = media_item[key]
                    if isinstance(val, (bytes, bytearray)):
                        return _open_bytes(bytes(val))
                    if isinstance(val, str):
                        # maybe base64 or path
                        if val.startswith("data:image/") and ";base64," in val:
                            b64 = val.split(";base64,", 1)[1]
                            try:
                                return _open_bytes(base64.b64decode(b64))
                            except Exception:
                                pass
                        if os.path.exists(val):
                            try:
                                return Image.open(val).convert("RGB")
                            except Exception:
                                pass
                        # fallback to treating as base64
                        try:
                            return _open_bytes(base64.b64decode(val))
                        except Exception:
                            pass

            # url/path keys
            for key in ("url", "uri", "path", "filename", "file"):
                if key in media_item and media_item[key]:
                    media_item = media_item[key]
                    break

        # If it's a string now, could be path, data URI, base64, or URL
        if isinstance(media_item, str):
            s = media_item.strip()
            # data URI
            if s.startswith("data:image/") and ";base64," in s:
                b64 = s.split(";base64,", 1)[1]
                try:
                    return _open_bytes(base64.b64decode(b64))
                except Exception:
                    return None

            # URL
            if s.startswith("http://") or s.startswith("https://"):
                try:
                    resp = requests.get(s, timeout=10)
                    resp.raise_for_status()
                    return _open_bytes(resp.content)
                except Exception as e:
                    if backend and hasattr(backend, "console"):
                        try:
                            backend.console.log(f"[red]Failed to fetch image URL: {e}")
                        except Exception:
                            pass
                    return None

            # Local file path
            if os.path.exists(s):
                try:
                    return Image.open(s).convert("RGB")
                except Exception as e:
                    if backend and hasattr(backend, "console"):
                        try:
                            backend.console.log(f"[red]Failed to open local image: {e}")
                        except Exception:
                            pass
                    return None

            # Try treating as base64
            try:
                return _open_bytes(base64.b64decode(s))
            except Exception:
                return None

        # Unable to handle
        return None

    def execute(
        self, prompt: str, config: dict = {}, batch_id=None, media=[], backend=None
    ) -> (str, str):
        has_image = False

        if media:
            has_image = True

        if batch_id is not None:
            output_file = f"/tmp/ircawp.flux2klein.{batch_id}.png"
        else:
            output_file = config.get("output_file", DEFAULT_FILENAME)

        skip_refinement = config.get("skip_refinement", False)

        scale_result = config.get("scale", 1.0)

        torch.cuda.empty_cache()

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

            # self.pipe.set_progress_bar_config(disable=True)

            print(
                "Generating size:", width, "x", height, "seed:", seed, "aspect:", aspect
            )

        prompt = prompt.strip()

        final_prompt = prompt

        if not skip_refinement and not has_image:
            refined_prompt = refinePrompt(prompt, backend, media)

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

        media_pil = []

        if has_image:
            for image_path in media:
                media_pil.append(self._load_image_from_media_item(image_path, backend))

            # if the image is < 1024px on the longest side, adjust scale_result accordingly so it's at least 1024px on longest side
            if media_pil[0] is not None:
                longest_side = max(media_pil[0].width, media_pil[0].height)
                if longest_side < MAX_WIDTH_HEIGHT:
                    print("Adjusting scale_result for small input image!")
                    scale_result = MAX_WIDTH_HEIGHT / longest_side
                if longest_side > MAX_WIDTH_HEIGHT:
                    print("Adjusting scale_result for large input image!")
                    scale_result = MAX_WIDTH_HEIGHT / longest_side

            width = int(media_pil[0].width * scale_result)
            height = int(media_pil[0].height * scale_result)
            aspect = width / height
            print(
                "Generating size (final):",
                width,
                "x",
                height,
                "media_pil[0].width",
                media_pil[0].width,
                "media_pil[0].height",
                media_pil[0].height,
                "seed:",
                seed,
                "aspect:",
                aspect,
                "scale_result",
                scale_result,
            )

        output_image = self.pipe(
            prompt=final_prompt,
            width=width,
            height=height,
            num_inference_steps=INF_STEPS,
            guidance_scale=CFG_SCALE,
            generator=torch.Generator("cpu").manual_seed(seed),
            image=media_pil,
        ).images[0]

        self._save_image_with_metadata(
            output_image,
            output_file,
            final_prompt,
            seed=seed,
            model="flux2klein",
            guidance_scale=CFG_SCALE,
            inference_steps=INF_STEPS,
            width=width,
            height=height,
            aspect_ratio=str(aspect),
        )

        self.last_imagegen_prompt = final_prompt.strip()

        # upscaled_file = upscaleImage(image, scale=2)

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

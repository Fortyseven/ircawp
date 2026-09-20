#!/usr/bin/env python3
"""
Quick image generation client for the media-server.

Usage: python scripts/gen_image.py "a red fox in a snowy forest" [options]
       python scripts/gen_image.py "make it blue" --input fox.png [options]

Options:
  --input FILE   Input image to edit (repeatable, up to 10). Routes to /images/edits.
  --out FILE     Output .png path (default: /tmp/ircawp_generated/<timestamp>.png)
  --server URL   Media-server base URL (default: http://localhost:8100)
  --model ID     Backend to use (default: server default)
  --size WxH     Output size, e.g. 1024x1024 (default: backend default)
"""

import argparse
import base64
import json
import sys
import time
import urllib.request
from pathlib import Path


def _image_data_url(path: Path) -> str:
    """Encode a local image file as a base64 data URL."""
    suffix = path.suffix.lower().lstrip(".")
    mime = {
        "jpg": "jpeg",
        "jpeg": "jpeg",
        "png": "png",
        "webp": "webp",
        "gif": "gif",
    }.get(suffix, "png")
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/{mime};base64,{b64}"


def generate(
    prompt: str,
    server: str = "http://localhost:8100",
    model: str | None = None,
    size: str | None = None,
    out: str | None = None,
    inputs: list[str] | None = None,
) -> Path:
    payload: dict = {"prompt": prompt}
    if model:
        payload["model"] = model
    if size:
        payload["size"] = size

    if inputs:
        if len(inputs) > 10:
            print("error: at most 10 input images", file=sys.stderr)
            sys.exit(1)
        payload["images"] = [
            {"image_url": _image_data_url(Path(p))} for p in inputs if Path(p).is_file()
        ]
        if not payload["images"]:
            print("error: no valid input image files", file=sys.stderr)
            sys.exit(1)
        endpoint = "/images/edits"
    else:
        endpoint = "/images/generations"

    req = urllib.request.Request(
        f"{server.rstrip('/')}{endpoint}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    t0 = time.time()
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.load(resp)
    elapsed = time.time() - t0

    images = data.get("data", [])
    if not images or not images[0].get("b64_json"):
        print(f"error: no image in response: {data}", file=sys.stderr)
        sys.exit(1)

    image_bytes = base64.b64decode(images[0]["b64_json"])

    if out is None:
        out_dir = Path("/tmp/ircawp_generated")
        out_dir.mkdir(parents=True, exist_ok=True)
        out = str(out_dir / f"gen_{int(time.time())}.png")
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(image_bytes)

    revised = images[0].get("revised_prompt")
    print(f"{out_path} ({len(image_bytes)} bytes, {elapsed:.1f}s)")
    if revised and revised != prompt:
        print(f"revised_prompt: {revised}")
    return out_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate an image via the media-server"
    )
    parser.add_argument("prompt", help="Text prompt")
    parser.add_argument(
        "--input",
        action="append",
        default=None,
        help="Input image to edit (repeatable, up to 10)",
    )
    parser.add_argument("--out", help="Output .png path")
    parser.add_argument(
        "--server", default="http://localhost:8100", help="Media-server base URL"
    )
    parser.add_argument(
        "--model", default=None, help="Backend to use (default: server default)"
    )
    parser.add_argument("--size", default=None, help="Output size, e.g. 1024x1024")
    args = parser.parse_args()

    generate(
        prompt=args.prompt,
        server=args.server,
        model=args.model,
        size=args.size,
        out=args.out,
        inputs=args.input,
    )


if __name__ == "__main__":
    main()

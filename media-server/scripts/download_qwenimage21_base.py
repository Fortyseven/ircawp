#!/usr/bin/env python3
"""
One-time download of the Qwen-Image-2.1 base model components (text encoder,
VAE, tokenizer, processor, configs) for OFFLINE media-server deployments.

The transformer is NOT downloaded here — it's the local GGUF file. This grabs
everything else the pipeline needs from the base repo, so the server can run
with no network access.

Usage (on a machine WITH network):
    uv run python scripts/download_qwenimage21_base.py
    uv run python scripts/download_qwenimage21_base.py --out /path/to/dir

Then on the offline server, set in config.yml:
    backends:
        qwenimage21:
            base_model: "/path/to/dir"
"""

import argparse
import os
from pathlib import Path

DEFAULT_OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "models",
    "Qwen-Image-2.1-base",
)

REPO_ID = "Qwen/Qwen-Image-2.1"

# Everything the pipeline loads EXCEPT the transformer (that's our GGUF).
ALLOWED_PATTERNS = [
    "text_encoder/**",
    "text_encoder/*.safetensors",
    "vae/**",
    "vae/*.safetensors",
    "tokenizer/**",
    "processor/**",
    "*.json",
    "*.txt",
    "*.model",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out", default=DEFAULT_OUT, help="Local directory to download into"
    )
    args = parser.parse_args()

    from huggingface_hub import snapshot_download

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {REPO_ID} (excluding transformer/) → {out}")
    snapshot_download(
        repo_id=REPO_ID,
        local_dir=str(out),
        allow_patterns=ALLOWED_PATTERNS,
        ignore_patterns=["transformer/**"],
    )
    print(f'Done. Set backends.qwenimage21.base_model: "{out}" in config.yml')


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Convert official Qwen/Qwen-Image-2.1 transformer safetensors to an f32 GGUF.

The output is then quantized with llama.cpp's `llama-quantize` to Q4_K_S.
The resulting GGUF has the same 297 tensor names as the official safetensors,
so it loads directly into diffusers' QwenImage21Transformer2DModel via
`from_single_file` + GGUFQuantizationConfig.

Usage:
    uv run python scripts/convert_qwenimage21_to_gguf.py \
        --repo Qwen/Qwen-Image-2.1 \
        --out /tmp/qwen_image_2.1_f32.gguf
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

import gguf
import numpy as np
import torch
from huggingface_hub import hf_hub_download


def read_safetensors_header(path: Path) -> dict:
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        return json.loads(f.read(n))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="Qwen/Qwen-Image-2.1")
    ap.add_argument("--out", default="/tmp/qwen_image_2.1_f32.gguf")
    args = ap.parse_args()

    # Discover shards from the index.
    index_path = hf_hub_download(
        args.repo, "transformer/diffusion_pytorch_model.safetensors.index.json"
    )
    index = json.loads(Path(index_path).read_text())
    weight_map: dict[str, str] = index["weight_map"]
    shards = sorted(set(weight_map.values()))
    print(f"shards: {shards}")

    out = Path(args.out)
    # NOTE: arch is spoofed as "qwen2" because llama-quantize only accepts
    # llama.cpp-registered LLM architectures (this build has no diffusion archs).
    # The arch string is irrelevant to diffusers' GGUF loader (it only reads
    # tensors by name). qwen2 7B profile (32 blocks x 4096 dims) matches
    # Qwen-Image-2.1's 32 blocks x 4096 dims, so the hparams are honest.
    writer = gguf.GGUFWriter(out, arch="qwen2", use_temp_file=True)
    writer.add_name("Qwen-Image-2.1 (official, f32)")
    writer.add_description("Converted from Qwen/Qwen-Image-2.1 official safetensors")
    writer.add_source_repo_url(f"https://huggingface.co/{args.repo}")
    # Required by llama_model_base::load_hparams (arch check in llama-quantize).
    writer.add_context_length(4096)
    writer.add_embedding_length(4096)
    writer.add_block_count(32)
    writer.add_layer_norm_rms_eps(1e-6)

    total = 0
    for shard in shards:
        shard_path = Path(hf_hub_download(args.repo, f"transformer/{shard}"))
        header = read_safetensors_header(shard_path)
        # data offset = 8 + header_len
        with open(shard_path, "rb") as f:
            f.seek(8 + struct.unpack("<Q", f.read(8))[0])
            for name, meta in header.items():
                if name == "__metadata__":
                    continue
                shape = meta["shape"]
                dtype = meta["dtype"]
                nbytes = (
                    int(np.prod(shape))
                    * {
                        "F32": 4,
                        "F16": 2,
                        "BF16": 2,
                        "I64": 8,
                        "I32": 4,
                        "I16": 2,
                        "I8": 1,
                        "U8": 1,
                        "F64": 8,
                    }[dtype]
                )
                raw = f.read(nbytes)
                if dtype == "BF16":
                    t = (
                        torch.frombuffer(raw, dtype=torch.uint8)
                        .view(torch.bfloat16)
                        .to(torch.float32)
                    )
                elif dtype == "F16":
                    t = (
                        torch.frombuffer(raw, dtype=torch.uint8)
                        .view(torch.float16)
                        .to(torch.float32)
                    )
                elif dtype == "F32":
                    t = torch.frombuffer(raw, dtype=torch.uint8).view(torch.float32)
                else:
                    raise ValueError(f"unsupported dtype {dtype} for {name}")
                arr = t.numpy().astype(np.float32)
                writer.add_tensor(
                    name, arr, raw_shape=shape, raw_dtype=gguf.GGMLQuantizationType.F32
                )
                total += 1
                if total % 32 == 0:
                    print(f"  {total} tensors ...", flush=True)
        print(f"shard {shard} done ({total} tensors total)", flush=True)

    writer.write_header_to_file()
    writer.write_kv_data_to_file()
    writer.write_tensors_to_file()  # internally calls write_ti_data_to_file()
    writer.close()
    print(f"wrote {out} ({total} tensors, {out.stat().st_size / 1e9:.2f} GB)")


if __name__ == "__main__":
    sys.exit(main())

"""
ircawp media-server: image generation HTTP service.

OpenAI-compatible API:
  POST /images/generations  — text-to-image
  POST /images/edits        — image editing

Strictly prompt-in → image-out. No LLM calls, no prompt refinement.
All refinement logic lives in the main ircawp bot.
"""

from __future__ import annotations

import base64
import io
import json
import os
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from PIL import Image
from rich.console import Console

from app.models import (
    Image,
    ImageEditRequest,
    ImageGenerationRequest,
    ImagesResponse,
    ensure_divisible_by_16,
    parse_size,
)

console = Console()


def load_config(path: str = "config.yml") -> dict:
    config_path = Path(__file__).parent.parent / path
    if not config_path.is_file():
        return {}
    with open(config_path) as f:
        return yaml.safe_load(f) or {}


CONFIG = load_config()
SERVER_CONFIG = CONFIG.get("server", {})
OUTPUT_DIR = Path(CONFIG.get("output_dir", "/tmp/ircawp_generated"))
DEFAULT_BACKEND = CONFIG.get("backend", "flux2klein")

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# Cache of backend instances (keeps models in memory across requests)
_backend_cache = {}


def get_backend(backend_id: str):
    """Lazy-load a backend by ID, caching the instance so the model stays in memory."""
    if backend_id in _backend_cache:
        return _backend_cache[backend_id]

    import importlib

    try:
        module = importlib.import_module(f"app.backends.{backend_id}")
    except ModuleNotFoundError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Backend '{backend_id}' not found: {e}",
        )

    backend_class = getattr(module, backend_id, None)
    if backend_class is None:
        raise HTTPException(
            status_code=400,
            detail=f"Backend module '{backend_id}' has no '{backend_id}' class",
        )

    instance = backend_class()
    _backend_cache[backend_id] = instance
    return instance


def _detect_mime(image_path: str) -> str:
    """Detect mime type from file extension."""
    ext = Path(image_path).suffix.lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    return mime_map.get(ext, "image/png")


def _image_to_response(image_path: str, final_prompt: str | None = None) -> Image:
    """Convert a generated image file to an Image response object."""
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    image_b64 = base64.b64encode(image_bytes).decode("ascii")

    img = Image(
        b64_json=image_b64,
    )
    if final_prompt:
        img.revised_prompt = final_prompt
    return img


def _build_backend_config(
    *,
    size: Optional[str],
    quality: Optional[str],
    batch_id=None,
    extra: dict | None = None,
) -> dict:
    """Build the config dict passed to backend.execute() from request params."""
    config = {}

    if extra:
        config.update(extra)

    # Parse size into width/height if provided
    parsed = parse_size(size)
    if parsed:
        width, height = ensure_divisible_by_16(*parsed)
        config["width"] = width
        config["height"] = height
    elif size:
        # Invalid size string — let the backend use its default
        pass

    # Map quality to remaster flag
    if quality == "high":
        config["remaster"] = True
    elif quality == "low":
        config["remaster"] = False
    # "standard", "medium", "auto", "hd" — don't set remaster

    if batch_id is not None:
        config["batch_id"] = batch_id

    return config


def _decode_image_url(image_url: str) -> bytes:
    """Decode a data URL or return raw bytes for a base64 string."""
    if image_url.startswith("data:"):
        # data:image/png;base64,...
        header, b64_data = image_url.split(",", 1)
        return base64.b64decode(b64_data)
    elif image_url.startswith("http://") or image_url.startswith("https://"):
        raise HTTPException(
            status_code=400,
            detail="External URLs are not supported for image input. Use base64 data URLs.",
        )
    else:
        # Assume it's a raw base64 string
        return base64.b64decode(image_url)


@asynccontextmanager
async def lifespan(app: FastAPI):
    console.log("[green]Media server starting")
    console.log(f"  backend: {DEFAULT_BACKEND}")
    console.log(f"  output_dir: {OUTPUT_DIR}")
    console.log(f"  host: {SERVER_CONFIG.get('host', '0.0.0.0')}")
    console.log(f"  port: {SERVER_CONFIG.get('port', 8100)}")
    yield
    console.log("[yellow]Media server shutting down")


app = FastAPI(
    title="ircawp Media Server",
    description="OpenAI-compatible image generation service for ircawp bot",
    version="0.2.0",
    lifespan=lifespan,
)


# ── Health & Static ─────────────────────────────────────────────


@app.get("/health")
async def health():
    return {"status": "ok", "backend": DEFAULT_BACKEND, "output_dir": str(OUTPUT_DIR)}


@app.get("/image/{filename}")
async def serve_image(filename: str):
    """Serve a generated image by filename."""
    image_path = OUTPUT_DIR / filename
    if not image_path.is_file():
        raise HTTPException(status_code=404, detail=f"Image not found: {filename}")
    return FileResponse(image_path, media_type="image/png")


# ── POST /images/generations ────────────────────────────────────


@app.post("/images/generations", response_model=ImagesResponse)
async def images_generations(req: ImageGenerationRequest) -> ImagesResponse:
    """Create images from a text prompt (OpenAI-compatible)."""
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt is required")

    backend_id = req.model or DEFAULT_BACKEND
    n = req.n

    # Validate n cap
    if n > 4:
        raise HTTPException(status_code=400, detail="n must be between 1 and 4")

    backend = get_backend(backend_id)
    results = []

    for i in range(n):
        batch_id = i if n > 1 else None
        config = _build_backend_config(
            size=req.size,
            quality=req.quality,
            batch_id=batch_id,
        )

        console.log(f"[cyan]Generating ({i+1}/{n}) with {backend_id}: {req.prompt}...")

        try:
            result = backend.execute(
                prompt=req.prompt.strip(),
                config=config,
                media=[],
            )

            # Handle both (path, prompt) tuple and single path return
            if isinstance(result, tuple):
                image_path, final_prompt = result
            else:
                image_path = result
                final_prompt = None

            console.log(f"[green]Generated ({i+1}/{n}): {image_path}")

            img = _image_to_response(image_path, final_prompt)
            results.append(img)

        except HTTPException:
            raise
        except Exception as e:
            console.log(f"[red]Generation ({i+1}/{n}) failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return ImagesResponse(
        created=int(time.time()),
        data=results,
    )


# ── POST /images/edits ──────────────────────────────────────────


@app.post("/images/edits", response_model=ImagesResponse)
async def images_edits(req: ImageEditRequest) -> ImagesResponse:
    """Create edited/extended images from input images + prompt (OpenAI-compatible)."""
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt is required")

    if not req.images:
        raise HTTPException(status_code=400, detail="At least one input image is required")

    backend_id = req.model or DEFAULT_BACKEND
    n = req.n

    if n > 4:
        raise HTTPException(status_code=400, detail="n must be between 1 and 4")

    # Decode input images to temp files
    temp_media_paths = []
    try:
        for img_ref in req.images:
            if img_ref.image_url:
                image_bytes = _decode_image_url(img_ref.image_url)
            elif img_ref.file_id:
                # file_id is treated as a local path or filename in OUTPUT_DIR
                image_path = OUTPUT_DIR / img_ref.file_id
                if image_path.is_file():
                    image_bytes = image_path.read_bytes()
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File not found: {img_ref.file_id}",
                    )
            else:
                continue

            temp_path = Path(tempfile.mkdtemp()) / f"input_{len(temp_media_paths)}.png"
            temp_path.write_bytes(image_bytes)
            temp_media_paths.append(str(temp_path))

        if not temp_media_paths:
            raise HTTPException(status_code=400, detail="No valid input images provided")

        backend = get_backend(backend_id)
        results = []

        for i in range(n):
            batch_id = i if n > 1 else None
            config = _build_backend_config(
                size=req.size,
                quality=req.quality,
                batch_id=batch_id,
            )

            console.log(f"[cyan]Editing ({i+1}/{n}) with {backend_id}: {req.prompt[:80]}...")

            try:
                result = backend.execute(
                    prompt=req.prompt.strip(),
                    config=config,
                    media=temp_media_paths,
                )

                if isinstance(result, tuple):
                    image_path, final_prompt = result
                else:
                    image_path = result
                    final_prompt = None

                console.log(f"[green]Edited ({i+1}/{n}): {image_path}")

                img = _image_to_response(image_path, final_prompt)
                results.append(img)

            except HTTPException:
                raise
            except Exception as e:
                console.log(f"[red]Edit ({i+1}/{n}) failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        return ImagesResponse(
            created=int(time.time()),
            data=results,
        )

    finally:
        # Cleanup temp files
        import shutil

        for temp_dir in set(str(Path(p).parent) for p in temp_media_paths):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass


# ── CLI Entry Point ─────────────────────────────────────────────


def start():
    """CLI entry point."""
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=SERVER_CONFIG.get("host", "0.0.0.0"),
        port=SERVER_CONFIG.get("port", 8100),
        reload=True,
    )


if __name__ == "__main__":
    start()

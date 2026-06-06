"""
ircawp media-server: image generation HTTP service.

Strictly prompt-in → image-out. No LLM calls, no prompt refinement.
All refinement logic lives in the main ircawp bot.
"""

from __future__ import annotations

import base64
import json
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import yaml
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from rich.console import Console

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


def get_backend(backend_id: str):
    """Lazy-load a backend by ID."""
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

    return backend_class()


@asynccontextmanager
async def lifespan(app: FastAPI):
    console.log(f"[green]Media server starting")
    console.log(f"  backend: {DEFAULT_BACKEND}")
    console.log(f"  output_dir: {OUTPUT_DIR}")
    console.log(f"  host: {SERVER_CONFIG.get('host', '0.0.0.0')}")
    console.log(f"  port: {SERVER_CONFIG.get('port', 8100)}")
    yield
    console.log("[yellow]Media server shutting down")


app = FastAPI(
    title="ircawp Media Server",
    description="Image generation service for ircawp bot",
    version="0.1.0",
    lifespan=lifespan,
)


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


@app.post("/generate")
async def generate(
    prompt: str = Form(...),
    backend_id: str = Form(default=DEFAULT_BACKEND),
    config_json: str = Form(default="{}"),
    media: list[UploadFile] = File(default=[]),
):
    """Generate an image from a prompt.

    Args:
        prompt: Final, ready-to-use prompt (refinement already done by caller)
        backend_id: Which backend to use (e.g. 'flux2klein')
        config_json: JSON config string (aspect, scale, batch_id, remaster, etc.)
        media: Optional input images for img2img workflows
    """
    if not prompt or not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt is required")

    # Parse config
    try:
        config = json.loads(config_json)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid config JSON: {e}")

    # Save uploaded media to temp files
    temp_media_paths = []
    try:
        for file in media:
            if file and file.filename:
                temp_path = Path(tempfile.mkdtemp()) / file.filename
                with open(temp_path, "wb") as f:
                    content = await file.read()
                    f.write(content)
                temp_media_paths.append(str(temp_path))

        # Get backend instance
        backend = get_backend(backend_id)

        # Execute generation
        console.log(f"[cyan]Generating with {backend_id}: {prompt[:80]}...")
        result = backend.execute(
            prompt=prompt,
            config=config,
            media=temp_media_paths,
        )

        # Handle both (path, prompt) tuple and single path return
        if isinstance(result, tuple):
            image_path, final_prompt = result
        else:
            image_path = result
            final_prompt = prompt

        console.log(f"[green]Generated: {image_path}")

        # Read image file and encode as base64 for transfer
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        image_b64 = base64.b64encode(image_bytes).decode("ascii")

        # Detect mime type from extension
        ext = Path(image_path).suffix.lower()
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
        mime_type = mime_map.get(ext, "image/png")

        return JSONResponse(
            content={
                "image_data": image_b64,
                "mime_type": mime_type,
                "final_prompt": final_prompt,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        console.log(f"[red]Generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup temp media files
        import shutil

        for temp_dir in set(str(Path(p).parent) for p in temp_media_paths):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass


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

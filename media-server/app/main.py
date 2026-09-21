"""
ircawp media-server: image generation HTTP service.

OpenAI-compatible API:
  POST /images/generations  — text-to-image
  POST /images/edits        — image editing

Strictly prompt-in → image-out. No LLM calls, no prompt refinement.
All refinement logic lives in the main ircawp bot.
"""

from __future__ import annotations

import asyncio
import base64
import os
import shutil
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Event
from typing import Optional

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from rich.console import Console

from app.backends.MediaBackend import GenerationCancelled
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
DEFAULT_BACKEND = CONFIG.get("backend", "flux2klein")

# Temporary directory for generated images (cleaned up on shutdown)
_TEMP_DIR = Path(tempfile.mkdtemp())


def _new_temp_file(suffix=".png") -> Path:
    """Create a unique temp file path for a generated image."""
    return _TEMP_DIR / f"img_{time.time_ns()}{suffix}"


# Cache of backend instances (keeps models in memory across requests)
_backend_cache = {}
_active_cancellations: dict[str, Event] = {}


def _register_cancellation(request_id: str | None) -> Event | None:
    if request_id is None:
        return None
    cancellation_event = Event()
    _active_cancellations[request_id] = cancellation_event
    return cancellation_event


def _unregister_cancellation(
    request_id: str | None, cancellation_event: Event | None
) -> None:
    if (
        request_id is not None
        and cancellation_event is not None
        and _active_cancellations.get(request_id) is cancellation_event
    ):
        del _active_cancellations[request_id]


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

    backend_config = CONFIG.get("backends", {}).get(backend_id, {})
    instance = backend_class(backend_config)
    _backend_cache[backend_id] = instance
    return instance


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
    backend_id: str,
    size: Optional[str],
    output_size: Optional[int],
    true_cfg_scale: Optional[float],
    seed: Optional[int],
    quality: Optional[str],
    batch_id=None,
    output_file: Optional[str] = None,
    extra: dict | None = None,
) -> dict:
    """Build the config dict passed to backend.execute() from request params.

    Per-backend settings from config.yml (backends.<id>) form the base;
    request-derived values (size, quality, output_file) override them.
    """
    config = dict(CONFIG.get("backends", {}).get(backend_id, {}))

    if extra:
        config.update(extra)

    if output_file:
        config["output_file"] = output_file

    if output_size is not None:
        config["max_output_size"] = output_size

    if backend_id == "qwenimage21" and true_cfg_scale is not None:
        config["true_cfg_scale"] = true_cfg_scale

    if backend_id == "qwenimage21" and seed is not None:
        config["seed"] = seed

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
    ssl_cert = SERVER_CONFIG.get("ssl_cert")
    ssl_key = SERVER_CONFIG.get("ssl_key")
    scheme = "https" if (ssl_cert and ssl_key) else "http"

    console.log("[green]Media server starting")
    console.log(f"  backend: {DEFAULT_BACKEND}")
    console.log(f"  temp_dir: {_TEMP_DIR}")
    console.log(
        f"  {scheme}://{SERVER_CONFIG.get('host', '0.0.0.0')}:{SERVER_CONFIG.get('port', 8100)}"
    )
    yield
    console.log("[yellow]Media server shutting down")
    shutil.rmtree(_TEMP_DIR, ignore_errors=True)


app = FastAPI(
    title="ircawp Media Server",
    description="OpenAI-compatible image generation service for ircawp bot",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    #    allow_origins=["http://localhost:5173", "https://fortyseven.github.io/chit-v2/"],
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ──────────────────────────────────────────────────────


@app.get("/health")
async def health():
    return {"status": "ok", "backend": DEFAULT_BACKEND}


@app.get("/backends")
async def backends():
    return {
        "default": DEFAULT_BACKEND,
        "backends": sorted((CONFIG.get("backends") or {}).keys()),
    }


@app.post("/images/cancellations/{request_id}", status_code=202)
async def cancel_image_request(request_id: str):
    cancellation_event = _active_cancellations.get(request_id)
    if cancellation_event is None:
        raise HTTPException(status_code=404, detail="Request not found")
    cancellation_event.set()
    return {"request_id": request_id, "status": "cancelling"}


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

    cancellation_event = _register_cancellation(req.request_id)
    try:
        try:
            backend = get_backend(backend_id)
        except HTTPException:
            raise
        except Exception as e:
            console.log(f"[red]Backend '{backend_id}' failed to load: {e}")
            raise HTTPException(status_code=500, detail=f"Backend load failed: {e}")

        results = []

        for i in range(n):
            batch_id = i if n > 1 else None
            output_file = str(_new_temp_file())
            config = _build_backend_config(
                backend_id=backend_id,
                size=req.size,
                output_size=req.output_size,
                true_cfg_scale=req.true_cfg_scale,
                seed=req.seed,
                quality=req.quality,
                batch_id=batch_id,
                output_file=output_file,
                extra={"steps": req.steps} if req.steps is not None else None,
            )
            config["cancellation_event"] = cancellation_event

            console.log(
                f"[cyan]Generating ({i + 1}/{n}) with {backend_id}"
                + (f": {req.prompt}" if req.verbose else "")
            )

            try:
                result = await asyncio.to_thread(
                    backend.execute,
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

                console.log(f"[green]Generated ({i + 1}/{n})")

                img = _image_to_response(image_path, final_prompt)
                results.append(img)

                # Remove temp file — image is already encoded in the response
                Path(image_path).unlink(missing_ok=True)

            except GenerationCancelled:
                Path(output_file).unlink(missing_ok=True)
                raise HTTPException(status_code=409, detail="Generation cancelled")
            except HTTPException:
                raise
            except Exception as e:
                console.log(f"[red]Generation ({i + 1}/{n}) failed: {e}")
                Path(output_file).unlink(missing_ok=True)
                raise HTTPException(status_code=500, detail=str(e))

        return ImagesResponse(
            created=int(time.time()),
            data=results,
        )
    finally:
        _unregister_cancellation(req.request_id, cancellation_event)


# ── POST /images/edits ──────────────────────────────────────────


@app.post("/images/edits", response_model=ImagesResponse)
async def images_edits(req: ImageEditRequest) -> ImagesResponse:
    """Create edited/extended images from input images + prompt (OpenAI-compatible)."""
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt is required")

    if not req.images:
        raise HTTPException(
            status_code=400, detail="At least one input image is required"
        )

    backend_id = req.model or DEFAULT_BACKEND
    n = req.n

    if n > 4:
        raise HTTPException(status_code=400, detail="n must be between 1 and 4")

    cancellation_event = _register_cancellation(req.request_id)
    # Decode input images to temp files
    temp_dir = Path(tempfile.mkdtemp())
    temp_media_paths = []
    try:
        for img_ref in req.images:
            if not img_ref.image_url:
                continue

            image_bytes = _decode_image_url(img_ref.image_url)
            temp_path = temp_dir / f"input_{len(temp_media_paths)}.png"
            temp_path.write_bytes(image_bytes)
            temp_media_paths.append(str(temp_path))

        if not temp_media_paths:
            raise HTTPException(
                status_code=400, detail="No valid input images provided"
            )

        try:
            backend = get_backend(backend_id)
        except HTTPException:
            raise
        except Exception as e:
            console.log(f"[red]Backend '{backend_id}' failed to load: {e}")
            raise HTTPException(status_code=500, detail=f"Backend load failed: {e}")

        results = []

        for i in range(n):
            batch_id = i if n > 1 else None
            output_file = str(_new_temp_file())
            config = _build_backend_config(
                backend_id=backend_id,
                size=req.size,
                output_size=req.output_size,
                true_cfg_scale=req.true_cfg_scale,
                seed=req.seed,
                quality=req.quality,
                batch_id=batch_id,
                output_file=output_file,
                extra={"steps": req.steps} if req.steps is not None else None,
            )
            config["cancellation_event"] = cancellation_event

            console.log(
                f"[cyan]Editing ({i + 1}/{n}) with {backend_id}"
                + (f": {req.prompt}" if req.verbose else "")
            )

            try:
                result = await asyncio.to_thread(
                    backend.execute,
                    prompt=req.prompt.strip(),
                    config=config,
                    media=temp_media_paths,
                )

                if isinstance(result, tuple):
                    image_path, final_prompt = result
                else:
                    image_path = result
                    final_prompt = None

                console.log(f"[green]Edited ({i + 1}/{n})")

                img = _image_to_response(image_path, final_prompt)
                results.append(img)

                # Remove temp file — image is already encoded in the response
                Path(image_path).unlink(missing_ok=True)

            except GenerationCancelled:
                Path(output_file).unlink(missing_ok=True)
                raise HTTPException(status_code=409, detail="Generation cancelled")
            except HTTPException:
                raise
            except Exception as e:
                console.log(f"[red]Edit ({i + 1}/{n}) failed: {e}")
                Path(output_file).unlink(missing_ok=True)
                raise HTTPException(status_code=500, detail=str(e))

        return ImagesResponse(
            created=int(time.time()),
            data=results,
        )

    finally:
        # Cleanup input temp files
        shutil.rmtree(temp_dir, ignore_errors=True)
        _unregister_cancellation(req.request_id, cancellation_event)


# ── Static Frontend Mount ───────────────────────────────────────
# Serve the built Svelte frontend (media-server/frontend/dist) at `/`.
# Mounted AFTER all API routes so API routes take precedence.
_FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if _FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=_FRONTEND_DIST, html=True), name="frontend")
else:
    console.log(
        f"[yellow]Frontend dist not found at {_FRONTEND_DIST} — serving API only"
    )


# ── CLI Entry Point ─────────────────────────────────────────────


def start():
    """CLI entry point."""
    import uvicorn

    ssl_cert = SERVER_CONFIG.get("ssl_cert")
    ssl_key = SERVER_CONFIG.get("ssl_key")

    # Expand ~ in paths — YAML stores them literally, ssl module won't
    if ssl_cert:
        ssl_cert = os.path.expanduser(ssl_cert)
    if ssl_key:
        ssl_key = os.path.expanduser(ssl_key)

    config = uvicorn.Config(
        app=app,
        host=SERVER_CONFIG.get("host", "0.0.0.0"),
        port=SERVER_CONFIG.get("port", 8100),
        ssl_certfile=ssl_cert or None,
        ssl_keyfile=ssl_key or None,
    )

    server = uvicorn.Server(config)
    server.run()


if __name__ == "__main__":
    start()

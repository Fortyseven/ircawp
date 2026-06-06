"""Pydantic models for the OpenAI-compatible images API."""

from __future__ import annotations

from typing import Annotated, Literal, Optional

from pydantic import BaseModel, Field


# ── Request Models ──────────────────────────────────────────────


class ImageRef(BaseModel):
    """A reference to an input image (URL or base64 data URL)."""

    file_id: Optional[str] = None
    image_url: Optional[str] = None

    def __bool__(self):
        return self.file_id is not None or self.image_url is not None


class ImageGenerationRequest(BaseModel):
    """Request body for POST /images/generations."""

    prompt: str = Field(..., min_length=1, max_length=32000, description="Text description of the desired image(s).")
    model: Optional[str] = Field(None, description="Backend/model to use (e.g. 'flux2klein'). Defaults to server default.")
    n: int = Field(1, ge=1, le=4, description="Number of images to generate (1-4).")
    size: Optional[str] = Field(None, description="Image size as 'WIDTHxHEIGHT', e.g. '1024x1024'.")
    quality: Optional[Literal["standard", "hd", "low", "medium", "high", "auto"]] = Field(
        None, description="Image quality. Maps to remaster flag for our backends."
    )
    response_format: Optional[Literal["url", "b64_json"]] = Field(
        None, description="Response format. We always return b64_json."
    )
    user: Optional[str] = Field(None, description="End-user identifier (ignored).")


class ImageEditRequest(BaseModel):
    """Request body for POST /images/edits."""

    prompt: str = Field(..., min_length=1, max_length=32000, description="Text description of the desired edit.")
    images: list[ImageRef] = Field(..., min_length=1, description="Input image(s) to edit.")
    model: Optional[str] = Field(None, description="Backend/model to use.")
    n: int = Field(1, ge=1, le=4, description="Number of edited images to generate (1-4).")
    size: Optional[str] = Field(None, description="Output image size as 'WIDTHxHEIGHT'.")
    quality: Optional[Literal["standard", "hd", "low", "medium", "high", "auto"]] = Field(
        None, description="Image quality."
    )
    input_fidelity: Optional[Literal["high", "low"]] = Field(None, description="Fidelity to original input.")
    mask: Optional[ImageRef] = Field(None, description="Mask image for inpainting.")
    user: Optional[str] = Field(None, description="End-user identifier (ignored).")


# ── Response Models ─────────────────────────────────────────────


class Image(BaseModel):
    """A single generated/edited image in the response."""

    b64_json: Optional[str] = Field(None, description="Base64-encoded image data.")
    url: Optional[str] = Field(None, description="URL of the generated image (not used).")
    revised_prompt: Optional[str] = Field(None, description="Revised prompt used for generation.")


class ImagesResponse(BaseModel):
    """Response body for image generation/edit endpoints."""

    created: int = Field(..., description="Unix timestamp (seconds) when the response was created.")
    data: list[Image] = Field(default_factory=list, description="List of generated images.")


# ── Size Parsing ────────────────────────────────────────────────


def parse_size(size_str: Optional[str]) -> tuple[int, int] | None:
    """Parse a 'WIDTHxHEIGHT' string into (width, height) ints.

    Returns None if size_str is None or invalid.
    """
    if not size_str:
        return None

    parts = size_str.split("x")
    if len(parts) != 2:
        return None

    try:
        width = int(parts[0])
        height = int(parts[1])
        if width <= 0 or height <= 0:
            return None
        return width, height
    except ValueError:
        return None


def ensure_divisible_by_16(width: int, height: int) -> tuple[int, int]:
    """Round dimensions to nearest multiple of 16 (required by diffusion models)."""
    return round(width / 16) * 16, round(height / 16) * 16

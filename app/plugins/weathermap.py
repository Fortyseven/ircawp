"""
Bot plugin to generate weather maps for a given location using the
OpenWeather Maps 1.0 API.
"""

import math
import os
import tempfile
from io import BytesIO

from PIL import Image
import numpy as np
import requests

from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend
from .__PluginBase import PluginBase
from .weather import _geocodeLocation


# Layer mapping: flag -> (layer_code, display_name)
# Uses OpenWeather Maps 1.0 (tile.openweathermap.org)
LAYERS = {
    "temps": ("temp_new", "Temperature"),
    "clouds": ("clouds_new", "Cloudiness"),
    "precip": ("precipitation_new", "Precipitation"),
    "rain": ("precipitation_new", "Precipitation"),
    "wind": ("wind_new", "Wind"),
}

# Default layer if no flag specified
DEFAULT_LAYER = "rain"

# Tile grid size (NxN)
GRID_SIZE = 3

# Zoom level (10 = regional view, ~117km coverage)
ZOOM = 5

# Tile size in pixels
TILE_SIZE = 256


def _lat_lon_to_tile(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    """Convert latitude/longitude to Web Mercator tile coordinates."""
    x = int((lon + 180.0) / 360.0 * (1 << zoom))
    lat_rad = math.radians(lat)
    y = int(
        (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi)
        / 2.0
        * (1 << zoom)
    )
    return x, y


def _fetch_base_tile(x: int, y: int, zoom: int) -> Image.Image | None:
    """Fetch a base map tile from OpenStreetMap."""
    url = f"https://tile.openstreetmap.org/{zoom}/{x}/{y}.png"
    headers = {
        "User-Agent": "ircawp-weathermap/1.0 (https://github.com/fortyseven/ircawp)"
    }
    try:
        resp = requests.get(url, timeout=10, headers=headers)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content))
    except Exception:
        return None


def _fetch_weather_tile(
    layer: str, x: int, y: int, zoom: int, api_key: str
) -> Image.Image | None:
    """Fetch a single weather map tile from OpenWeather Maps 1.0 API."""
    url = (
        f"https://tile.openweathermap.org/map/{layer}/{zoom}/{x}/{y}.png"
        f"?appid={api_key}"
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content))
    except Exception:
        return None


def _multiply_blend(base: Image.Image, overlay: Image.Image) -> Image.Image:
    """Apply Multiply blending with boosted opacity."""
    base_arr = np.array(base.convert("RGB")).astype(float) / 255.0
    over_arr = np.array(overlay.convert("RGBA")).astype(float) / 255.0

    rgb = over_arr[:, :, :3]
    alpha = over_arr[:, :, 3:4]  # keep as 4D for broadcasting

    # Boost alpha aggressively (2.5x, clamp to 1.0)
    alpha = np.clip(alpha * 2.5, 0.0, 1.0)

    # Multiply blend per channel
    blended = base_arr * rgb

    # Composite with boosted alpha
    result = blended * alpha + base_arr * (1.0 - alpha)
    result = np.clip(result, 0.0, 1.0)
    result = (result * 255).astype(np.uint8)
    return Image.fromarray(result, "RGB")


def _stitch_map(
    lat: float, lon: float, layer: str, zoom: int, api_key: str
) -> Image.Image | None:
    """Fetch a GRID_SIZE x GRID_SIZE tile grid (base + weather) and composite."""
    center_x, center_y = _lat_lon_to_tile(lat, lon, zoom)
    half = GRID_SIZE // 2

    # Stitch base map tiles
    base = Image.new("RGB", (TILE_SIZE * GRID_SIZE, TILE_SIZE * GRID_SIZE))
    for dy in range(GRID_SIZE):
        for dx in range(GRID_SIZE):
            tile = _fetch_base_tile(center_x + dx - half, center_y + dy - half, zoom)
            if tile:
                base.paste(tile.convert("RGB"), (dx * TILE_SIZE, dy * TILE_SIZE))

    # Stitch weather overlay tiles
    overlay = Image.new(
        "RGBA", (TILE_SIZE * GRID_SIZE, TILE_SIZE * GRID_SIZE), (0, 0, 0, 0)
    )
    for dy in range(GRID_SIZE):
        for dx in range(GRID_SIZE):
            tile = _fetch_weather_tile(
                layer, center_x + dx - half, center_y + dy - half, zoom, api_key
            )
            if tile:
                overlay.paste(tile, (dx * TILE_SIZE, dy * TILE_SIZE))

    # Composite with Overlay blend mode
    combined = _multiply_blend(base, overlay)
    return combined


def _parse_query(query: str) -> tuple[str, str, int]:
    """Parse the query to extract location, layer flag, and zoom level.
    Returns (location, layer_flag, zoom).
    """
    parts = query.strip().split()
    layer = DEFAULT_LAYER
    zoom = ZOOM

    # Check for layer flags
    for flag in LAYERS:
        if f"--{flag}" in parts:
            layer = flag
            break

    # Check for --zoom <N>
    for i, part in enumerate(parts):
        if part == "--zoom" and i + 1 < len(parts):
            try:
                zoom = int(parts[i + 1])
                zoom = max(1, min(18, zoom))  # clamp to valid tile range
            except ValueError:
                pass
            break

    # Remove flags from parts to get location
    skip_next = False
    location_parts = []
    for i, part in enumerate(parts):
        if skip_next:
            skip_next = False
            continue
        if part == "--zoom" and i + 1 < len(parts):
            skip_next = True
            continue
        if part.startswith("--"):
            continue
        location_parts.append(part)
    location = " ".join(location_parts) if location_parts else ""

    return location, layer, zoom


def doWeatherMap(
    query: str,
    media: list,
    backend: Ircawp_Backend,
    media_backend: MediaBackend = None,
) -> tuple[str, str, bool, dict]:
    try:
        # Get API key from config
        api_key = backend.config.get("weather", {}).get("api_key")
        if not api_key:
            return (
                "Weather API key not configured. Add 'weather.api_key' to config.yml",
                "",
                True,
                {},
            )

        # Parse query
        location_query, layer_flag, zoom = _parse_query(query)
        if not location_query:
            return (
                "No location provided. Usage: /weathermap <location> [--temps|--clouds|--precip|--wind] [--zoom N]",
                "",
                True,
                {},
            )

        layer_code, layer_name = LAYERS[layer_flag]

        # Geocode the location
        backend.console.log(f"[blue]Geocoding location: {location_query}")
        location_name, lat, lon = _geocodeLocation(location_query, api_key)
        backend.console.log(f"[green]Found: {location_name} ({lat}, {lon})")

        # Fetch and stitch the map
        backend.console.log(f"[blue]Fetching {layer_name} map tiles (zoom {zoom})")
        image = _stitch_map(lat, lon, layer_code, zoom, api_key)

        if image is None:
            return "Error: failed to generate weather map.", "", True, {}

        # Save to temp file
        fd, path = tempfile.mkstemp(suffix=".png", prefix="weathermap_")
        os.close(fd)
        image.save(path, "PNG")

        return (
            f"{layer_name} map for {location_name}:",
            path,
            True,
            {},
        )

    except ValueError as e:
        return f"Location error: {str(e)}", "", True, {}
    except Exception as e:
        return f"Weather map error: {str(e)}", "", True, {}


plugin = PluginBase(
    name="Weather Map Plugin",
    description="Get a weather map for a location",
    triggers=["weathermap"],
    system_prompt="Weather map for a location",
    emoji_prefix="🗺",
    msg_empty_query="No location provided. Usage: /weathermap <location> [--temps|--clouds|--precip|--wind]",
    msg_exception_prefix="WEATHER MAP ERROR",
    main=doWeatherMap,
    use_imagegen=False,
)

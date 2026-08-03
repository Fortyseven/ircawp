"""Tests for the weathermap plugin."""

import math
import pytest
from PIL import Image
import numpy as np
from app.plugins.weathermap import (
    _parse_query,
    _lat_lon_to_tile,
    _multiply_blend,
    _stitch_map,
    LAYERS,
    DEFAULT_LAYER,
    GRID_SIZE,
    ZOOM,
    TILE_SIZE,
    plugin,
)


class TestParseQuery:
    def test_location_only(self):
        location, layer, zoom = _parse_query("San Francisco")
        assert location == "San Francisco"
        assert layer == DEFAULT_LAYER
        assert zoom == ZOOM

    def test_flag_end(self):
        location, layer, zoom = _parse_query("San Francisco --wind")
        assert location == "San Francisco"
        assert layer == "wind"
        assert zoom == ZOOM

    def test_flag_start(self):
        location, layer, zoom = _parse_query("--clouds New York")
        assert location == "New York"
        assert layer == "clouds"
        assert zoom == ZOOM

    def test_flag_middle(self):
        location, layer, zoom = _parse_query("New --precip York")
        assert location == "New York"
        assert layer == "precip"
        assert zoom == ZOOM

    def test_rain_alias(self):
        location, layer, zoom = _parse_query("London --rain")
        assert location == "London"
        assert layer == "rain"
        assert zoom == ZOOM

    def test_temps_flag(self):
        location, layer, zoom = _parse_query("Tokyo --temps")
        assert location == "Tokyo"
        assert layer == "temps"
        assert zoom == ZOOM

    def test_unknown_flag_stripped(self):
        location, layer, zoom = _parse_query("Berlin --unknown")
        assert location == "Berlin"
        assert layer == DEFAULT_LAYER
        assert zoom == ZOOM

    def test_multi_word_location(self):
        location, layer, zoom = _parse_query("New York City --wind")
        assert location == "New York City"
        assert layer == "wind"
        assert zoom == ZOOM

    def test_empty_query(self):
        location, layer, zoom = _parse_query("")
        assert location == ""
        assert layer == DEFAULT_LAYER
        assert zoom == ZOOM

    def test_flag_only(self):
        location, layer, zoom = _parse_query("--wind")
        assert location == ""
        assert layer == "wind"
        assert zoom == ZOOM

    def test_zoom_override(self):
        location, layer, zoom = _parse_query("San Francisco --zoom 8")
        assert location == "San Francisco"
        assert layer == DEFAULT_LAYER
        assert zoom == 8

    def test_zoom_with_layer(self):
        location, layer, zoom = _parse_query("London --wind --zoom 12")
        assert location == "London"
        assert layer == "wind"
        assert zoom == 12

    def test_zoom_start(self):
        location, layer, zoom = _parse_query("--zoom 6 Tokyo")
        assert location == "Tokyo"
        assert layer == DEFAULT_LAYER
        assert zoom == 6

    def test_zoom_middle(self):
        location, layer, zoom = _parse_query("New --zoom 10 York --clouds")
        assert location == "New York"
        assert layer == "clouds"
        assert zoom == 10

    def test_zoom_clamped_low(self):
        location, layer, zoom = _parse_query("Berlin --zoom 0")
        assert zoom == 1

    def test_zoom_clamped_high(self):
        location, layer, zoom = _parse_query("Berlin --zoom 25")
        assert zoom == 18

    def test_zoom_invalid(self):
        location, layer, zoom = _parse_query("Berlin --zoom abc")
        assert zoom == ZOOM

    def test_zoom_no_value(self):
        location, layer, zoom = _parse_query("Berlin --zoom")
        assert zoom == ZOOM


class TestLatLonToTile:
    def test_san_francisco(self):
        x, y = _lat_lon_to_tile(37.7749, -122.4194, 6)
        assert x == 10
        assert y == 24

    def test_london(self):
        x, y = _lat_lon_to_tile(51.5074, -0.1278, 6)
        assert x == 31
        assert y == 21

    def test_tokyo(self):
        x, y = _lat_lon_to_tile(35.6762, 139.6503, 6)
        assert x == 56
        assert y == 25

    def test_equator(self):
        x, y = _lat_lon_to_tile(0.0, 0.0, 6)
        assert x == 32
        assert y == 32

    def test_different_zoom(self):
        x6, y6 = _lat_lon_to_tile(37.7749, -122.4194, 6)
        x7, y7 = _lat_lon_to_tile(37.7749, -122.4194, 7)
        # At zoom 7, tile should be 2x the zoom 6 tile (or +1)
        assert x7 in (x6 * 2, x6 * 2 + 1)
        assert y7 in (y6 * 2, y6 * 2 + 1)

    def test_poles_edge_case(self):
        # Near north pole should give y near 0
        _, y = _lat_lon_to_tile(89.0, 0.0, 6)
        assert y < 10

        # Near south pole should give y near max
        _, y = _lat_lon_to_tile(-89.0, 0.0, 6)
        assert y > 40


class TestLayers:
    def test_all_layers_have_code(self):
        for flag, (code, name) in LAYERS.items():
            assert code, f"Layer {flag} missing code"
            assert name, f"Layer {flag} missing name"

    def test_rain_maps_to_precip(self):
        assert LAYERS["rain"][0] == LAYERS["precip"][0]

    def test_default_layer_exists(self):
        assert DEFAULT_LAYER in LAYERS

    def test_expected_layers(self):
        expected = {"temps", "clouds", "precip", "rain", "wind"}
        assert set(LAYERS.keys()) == expected


class TestConstants:
    def test_grid_size_odd(self):
        # Grid size should be odd for proper centering
        assert GRID_SIZE % 2 == 1

    def test_tile_size(self):
        assert TILE_SIZE == 256

    def test_zoom_reasonable(self):
        # Zoom should be in a reasonable range for maps
        assert 3 <= ZOOM <= 15


class TestMultiplyBlend:
    def test_blend_produces_rgb(self):
        base = Image.new("RGB", (100, 100), (200, 200, 200))
        overlay = Image.new("RGBA", (100, 100), (100, 150, 200, 100))
        result = _multiply_blend(base, overlay)
        assert result.mode == "RGB"
        assert result.size == (100, 100)

    def test_blend_darkens(self):
        base = Image.new("RGB", (10, 10), (200, 200, 200))
        overlay = Image.new("RGBA", (10, 10), (100, 100, 100, 200))
        result = _multiply_blend(base, overlay)
        # Multiply should darken: result < base where overlay has color
        base_arr = np.array(base)
        result_arr = np.array(result)
        assert np.mean(result_arr) < np.mean(base_arr)

    def test_blend_translucent_overlay(self):
        base = Image.new("RGB", (10, 10), (200, 200, 200))
        overlay = Image.new("RGBA", (10, 10), (100, 100, 100, 0))
        result = _multiply_blend(base, overlay)
        # Zero alpha overlay should leave base unchanged
        result_arr = np.array(result)
        base_arr = np.array(base)
        np.testing.assert_array_equal(result_arr, base_arr)

    def test_blend_solid_overlay(self):
        base = Image.new("RGB", (10, 10), (200, 200, 200))
        overlay = Image.new("RGBA", (10, 10), (128, 128, 128, 255))
        result = _multiply_blend(base, overlay)
        # Full alpha multiply: 200 * 128/255 ≈ 100
        result_arr = np.array(result)
        expected = int(200 * 128 / 255)
        assert abs(result_arr[0, 0, 0] - expected) < 5


class TestPluginConfig:
    def test_plugin_name(self):
        assert plugin.name == "Weather Map Plugin"

    def test_plugin_triggers(self):
        assert "weathermap" in plugin.triggers

    def test_no_imagegen(self):
        assert plugin.use_imagegen is False

    def test_emoji_safe(self):
        # Emoji should be a single codepoint (no ZWJ)
        emoji = plugin.emoji_prefix
        try:
            emoji.encode("utf-8")
        except UnicodeEncodeError:
            pytest.fail(f"Emoji {emoji} is not UTF-8 safe")

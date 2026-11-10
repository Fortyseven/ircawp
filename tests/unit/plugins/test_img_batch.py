"""Tests for the /img batch grid compositor (app/plugins/_img_utils/batch.py)."""

import pytest
from PIL import Image

from app.plugins._img_utils.batch import _layout_for_count, _compose_grid


class TestLayoutForCount:
    def test_four_keeps_2x2(self):
        w, h, positions = _layout_for_count(4, 100, 50)
        assert (w, h) == (200, 100)
        assert positions == [(0, 0), (100, 0), (0, 50), (100, 50)]

    def test_two_landscape_stacks_vertically(self):
        # 100x50 landscape: vertical column, canvas 100x100
        w, h, positions = _layout_for_count(2, 100, 50)
        assert (w, h) == (100, 100)
        assert positions == [(0, 0), (0, 50)]

    def test_two_portrait_stacks_horizontally(self):
        # 50x100 portrait: horizontal row, canvas 100x100
        w, h, positions = _layout_for_count(2, 50, 100)
        assert (w, h) == (100, 100)
        assert positions == [(0, 0), (50, 0)]

    def test_three_landscape_stacks_vertically(self):
        w, h, positions = _layout_for_count(3, 100, 50)
        assert (w, h) == (100, 150)
        assert positions == [(0, 0), (0, 50), (0, 100)]

    def test_three_portrait_stacks_horizontally(self):
        w, h, positions = _layout_for_count(3, 50, 100)
        assert (w, h) == (150, 100)
        assert positions == [(0, 0), (50, 0), (100, 0)]

    def test_single_passthrough(self):
        w, h, positions = _layout_for_count(1, 100, 50)
        assert (w, h) == (100, 50)
        assert positions == [(0, 0)]

    def test_square_treated_as_landscape(self):
        # w >= h falls to the vertical stack
        w, h, positions = _layout_for_count(2, 50, 50)
        assert (w, h) == (50, 100)
        assert positions == [(0, 0), (0, 50)]


def _solid(path, size, color):
    """Write a solid-color PNG and return its path."""
    img = Image.new("RGB", size, color=color)
    img.save(str(path), format="PNG")
    return str(path)


def _dominant_channel(px):
    """Return the channel index (0=R, 1=G, 2=B) with the highest value."""
    return max(range(3), key=lambda i: px[i])


class TestComposeGrid:
    def test_two_landscape_no_black_padding(self, tmp_path, mock_backend):
        w, h = 100, 50
        red = _solid(tmp_path / "a.png", (w, h), (220, 0, 0))
        blue = _solid(tmp_path / "b.png", (w, h), (0, 0, 220))

        grid_path = _compose_grid([red, blue], mock_backend)
        assert grid_path == str(tmp_path / "a_grid.jpg")

        grid = Image.open(grid_path)
        assert grid.size == (w, 2 * h)
        # top half is image A (red), bottom half is image B (blue)
        assert _dominant_channel(grid.getpixel((w // 2, h // 2))) == 0
        assert _dominant_channel(grid.getpixel((w // 2, h + h // 2))) == 2
        # corner that was black under the old 2x2 layout is now image B
        assert _dominant_channel(grid.getpixel((w - 1, 2 * h - 1))) == 2

    def test_three_portrait_row(self, tmp_path, mock_backend):
        w, h = 50, 100
        red = _solid(tmp_path / "a.png", (w, h), (220, 0, 0))
        green = _solid(tmp_path / "b.png", (w, h), (0, 220, 0))
        blue = _solid(tmp_path / "c.png", (w, h), (0, 0, 220))

        grid_path = _compose_grid([red, green, blue], mock_backend)
        grid = Image.open(grid_path)
        assert grid.size == (3 * w, h)
        assert _dominant_channel(grid.getpixel((w // 2, h // 2))) == 0
        assert _dominant_channel(grid.getpixel((w + w // 2, h // 2))) == 1
        assert _dominant_channel(grid.getpixel((2 * w + w // 2, h // 2))) == 2

    def test_four_unchanged_2x2(self, tmp_path, mock_backend):
        w, h = 64, 32
        colors = [(220, 0, 0), (0, 220, 0), (0, 0, 220), (220, 220, 0)]
        paths = [
            _solid(tmp_path / f"img{i}.png", (w, h), colors[i]) for i in range(4)
        ]

        grid_path = _compose_grid(paths, mock_backend)
        grid = Image.open(grid_path)
        assert grid.size == (2 * w, 2 * h)
        # bottom-right cell is the 4th image (yellow), not black
        assert _dominant_channel(grid.getpixel((2 * w - 1, 2 * h - 1))) in (0, 1)

    def test_mixed_sizes_normalized_to_smallest(self, tmp_path, mock_backend):
        big = _solid(tmp_path / "a.png", (200, 100), (220, 0, 0))
        small = _solid(tmp_path / "b.png", (100, 50), (0, 0, 220))

        grid_path = _compose_grid([big, small], mock_backend)
        grid = Image.open(grid_path)
        assert grid.size == (100, 100)

    def test_missing_file_returns_empty_and_logs(self, tmp_path, mock_backend):
        red = _solid(tmp_path / "a.png", (100, 50), (220, 0, 0))
        result = _compose_grid([red, str(tmp_path / "nope.png")], mock_backend)
        assert result == ""
        assert any("grid compose failed" in m for m in mock_backend.console.messages)

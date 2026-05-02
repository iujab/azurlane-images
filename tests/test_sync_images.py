"""Tests for scripts/sync_images.py — additive-only sync logic."""
from pathlib import Path

import pytest
from PIL import Image

from scripts.sync_images import add_if_new


def make_png(path: Path, color: tuple[int, int, int] = (255, 0, 0)) -> None:
    """Write a tiny 4x4 PNG so tests don't need real game art."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (4, 4), color).save(path, "PNG")


class TestAddIfNew:
    def test_copies_png_to_png_when_dest_missing(self, tmp_path: Path):
        src = tmp_path / "src.png"
        dest = tmp_path / "out" / "dest.png"
        make_png(src, color=(10, 20, 30))

        added = add_if_new(src, dest)

        assert added is True
        assert dest.exists()
        with Image.open(dest) as img:
            assert img.size == (4, 4)

    def test_converts_png_to_webp_when_dest_is_webp(self, tmp_path: Path):
        src = tmp_path / "src.png"
        dest = tmp_path / "out" / "dest.webp"
        make_png(src, color=(10, 20, 30))

        added = add_if_new(src, dest)

        assert added is True
        assert dest.exists()
        with Image.open(dest) as img:
            assert img.format == "WEBP"
            assert img.size == (4, 4)

    def test_refuses_to_overwrite_existing_dest(self, tmp_path: Path):
        src = tmp_path / "src.png"
        dest = tmp_path / "dest.webp"
        make_png(src, color=(10, 20, 30))
        # Pre-seed dest with different content
        Image.new("RGB", (8, 8), (200, 200, 200)).save(dest, "WEBP")
        original_bytes = dest.read_bytes()

        added = add_if_new(src, dest)

        assert added is False
        assert dest.read_bytes() == original_bytes  # untouched

    def test_creates_parent_dirs_as_needed(self, tmp_path: Path):
        src = tmp_path / "src.png"
        dest = tmp_path / "deep" / "nested" / "dest.webp"
        make_png(src)

        added = add_if_new(src, dest)

        assert added is True
        assert dest.exists()

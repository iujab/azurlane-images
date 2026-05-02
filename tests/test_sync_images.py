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


from scripts.sync_images import sync_paintings, sync_thumbnails


class TestSyncPaintings:
    def test_adds_only_missing_webps(self, tmp_path: Path):
        extract_root = tmp_path / "ClientExtract" / "EN" / "painting"
        paintings_dir = tmp_path / "paintings"

        # Source: three PNGs from "azlassets"
        make_png(extract_root / "gin.png")
        make_png(extract_root / "belfast_3.png")
        make_png(extract_root / "new_skin_rw.png")

        # Pre-seed: gin.webp already exists in the repo
        paintings_dir.mkdir(parents=True)
        # Use a distinct existing file so we can prove it wasn't overwritten
        Image.new("RGB", (16, 16), (1, 2, 3)).save(
            paintings_dir / "gin.webp", "WEBP"
        )
        gin_original = (paintings_dir / "gin.webp").read_bytes()

        added = sync_paintings(extract_root, paintings_dir)

        assert added == 2  # belfast_3 + new_skin_rw, not gin
        assert (paintings_dir / "belfast_3.webp").exists()
        assert (paintings_dir / "new_skin_rw.webp").exists()
        # Untouched
        assert (paintings_dir / "gin.webp").read_bytes() == gin_original

    def test_handles_missing_extract_dir(self, tmp_path: Path):
        extract_root = tmp_path / "does_not_exist"
        paintings_dir = tmp_path / "paintings"
        paintings_dir.mkdir()

        added = sync_paintings(extract_root, paintings_dir)

        assert added == 0


class TestSyncThumbnails:
    def test_copies_pngs_unchanged(self, tmp_path: Path):
        extract_root = tmp_path / "ClientExtract" / "EN" / "shipyardicon"
        thumbs_dir = tmp_path / "thumbnails"

        make_png(extract_root / "10000.png", color=(50, 60, 70))
        make_png(extract_root / "20212.png", color=(80, 90, 100))

        added = sync_thumbnails(extract_root, thumbs_dir)

        assert added == 2
        # Verify these are PNGs, not converted
        with Image.open(thumbs_dir / "10000.png") as img:
            assert img.format == "PNG"

    def test_skips_existing_thumbnails(self, tmp_path: Path):
        extract_root = tmp_path / "ClientExtract" / "EN" / "shipyardicon"
        thumbs_dir = tmp_path / "thumbnails"

        make_png(extract_root / "10000.png")
        thumbs_dir.mkdir()
        # Pre-seed with a marker
        (thumbs_dir / "10000.png").write_bytes(b"PRE-EXISTING-MARKER")

        added = sync_thumbnails(extract_root, thumbs_dir)

        assert added == 0
        assert (thumbs_dir / "10000.png").read_bytes() == b"PRE-EXISTING-MARKER"

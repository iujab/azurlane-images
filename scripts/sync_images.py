"""Additive-only image sync from azlassets ClientExtract → repo paintings/ + thumbnails/.

Hard rule: never overwrite or delete existing files in the repo. The committed
copy is canonical; if upstream changes a skin's art, we keep our version.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image


def add_if_new(src: Path, dest: Path) -> bool:
    """Copy or convert src to dest only if dest does not already exist.

    - PNG → PNG: byte-copy (preserves exact upstream output).
    - PNG → WebP: lossless WebP encode via Pillow.
    - Any other suffix combo: byte-copy.

    Returns True if a new file was written, False if dest already existed.
    """
    if dest.exists():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() == ".png" and dest.suffix.lower() == ".webp":
        with Image.open(src) as img:
            img.save(dest, "WEBP", lossless=True, quality=100)
    else:
        shutil.copyfile(src, dest)
    return True


def sync_paintings(extract_dir: Path, target_dir: Path) -> int:
    """Walk extract_dir for *.png and write missing webps into target_dir.

    Returns the count of files added. Raises RuntimeError if two source PNGs
    in the same run map to the same target (silent data loss otherwise).
    """
    if not extract_dir.exists():
        return 0
    added = 0
    written_this_run: dict[Path, Path] = {}
    for png in sorted(extract_dir.rglob("*.png")):
        target = target_dir / f"{png.stem}.webp"
        if target in written_this_run:
            raise RuntimeError(
                f"paintings stem collision: {png} and {written_this_run[target]} "
                f"both map to {target}"
            )
        if add_if_new(png, target):
            added += 1
            written_this_run[target] = png
            print(f"+ paintings/{target.name}", flush=True)
    return added


def sync_thumbnails(extract_dir: Path, target_dir: Path) -> int:
    """Walk extract_dir for *.png and copy missing files into target_dir.

    Returns the count of files added. Raises RuntimeError if two source PNGs
    in the same run map to the same target (silent data loss otherwise).
    """
    if not extract_dir.exists():
        return 0
    added = 0
    written_this_run: dict[Path, Path] = {}
    for png in sorted(extract_dir.rglob("*.png")):
        target = target_dir / png.name
        if target in written_this_run:
            raise RuntimeError(
                f"thumbnails name collision: {png} and {written_this_run[target]} "
                f"both map to {target}"
            )
        if add_if_new(png, target):
            added += 1
            written_this_run[target] = png
            print(f"+ thumbnails/{target.name}", flush=True)
    return added

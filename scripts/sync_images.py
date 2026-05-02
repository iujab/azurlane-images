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

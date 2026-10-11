"""Additive-only image sync from azlassets ClientExtract → repo paintings/ + thumbnails/.

Hard rule: never overwrite or delete existing files in the repo. The committed
copy is canonical; if upstream changes a skin's art, we keep our version.
"""
from __future__ import annotations

import argparse
import shutil
import sys
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
    *both newly written this run* map to the same target — that path would
    otherwise lose data. If the target already existed in target_dir before
    this run, a second source pointing at it is a no-op skip (the additive
    invariant from add_if_new protects the existing file).
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
    *both newly written this run* map to the same target — that path would
    otherwise lose data. If the target already existed in target_dir before
    this run, a second source pointing at it is a no-op skip (the additive
    invariant from add_if_new protects the existing file).
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


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EXTRACT_ROOT = REPO_ROOT / "ClientExtract" / "EN"
DEFAULT_PAINTINGS_DEST = REPO_ROOT / "paintings"
DEFAULT_THUMBNAILS_DEST = REPO_ROOT / "thumbnails"


def _version_key(d: Path) -> tuple[int, ...]:
    """Sort key for versioned extract dirs ('PAINTING 662', 'AZL 9.3.384'): numeric parts, newest first."""
    parts = d.name.split(" ", 1)[-1].split(".")
    return tuple(int(x) if x.isdigit() else -1 for x in parts)


def find_extract_dirs(extract_root: Path, folder: str) -> list[Path]:
    """Return every ``<folder>/`` directory azlassets may have written under extract_root.

    azlassets <= 4 wrote ``ClientExtract/EN/painting/``; azlassets >= 5 writes one
    directory per extracted version, ``ClientExtract/EN/PAINTING 662/painting/`` or
    ``ClientExtract/EN/AZL 9.3.384/shipyardicon/``. Both layouts are returned,
    versioned ones newest first so the newest art wins a same-run name collision
    (the additive rule makes the older copy a no-op skip).
    """
    found = []
    flat = extract_root / folder
    if flat.is_dir():
        found.append(flat)
    versioned = [d for d in extract_root.glob(f"*/{folder}") if d.is_dir()]
    found.extend(sorted(versioned, key=_version_key, reverse=True))
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extract-root", type=Path, default=DEFAULT_EXTRACT_ROOT,
                        help="azlassets client extract dir; painting/ and shipyardicon/ are found under it (flat or versioned)")
    parser.add_argument("--paintings-src", type=Path, default=None, help="override: a single paintings source dir")
    parser.add_argument("--paintings-dest", type=Path, default=DEFAULT_PAINTINGS_DEST)
    parser.add_argument("--thumbnails-src", type=Path, default=None, help="override: a single thumbnails source dir")
    parser.add_argument("--thumbnails-dest", type=Path, default=DEFAULT_THUMBNAILS_DEST)
    args = parser.parse_args(argv)

    painting_dirs = [args.paintings_src] if args.paintings_src else find_extract_dirs(args.extract_root, "painting")
    thumbnail_dirs = [args.thumbnails_src] if args.thumbnails_src else find_extract_dirs(args.extract_root, "shipyardicon")
    print(f"painting sources: {[str(d) for d in painting_dirs] or 'none found'}")
    print(f"thumbnail sources: {[str(d) for d in thumbnail_dirs] or 'none found'}")

    paintings_added = sum(sync_paintings(d, args.paintings_dest) for d in painting_dirs)
    thumbnails_added = sum(sync_thumbnails(d, args.thumbnails_dest) for d in thumbnail_dirs)

    print(f"\n=== Summary ===")
    print(f"Added {paintings_added} paintings, {thumbnails_added} thumbnails")
    return 0


if __name__ == "__main__":
    sys.exit(main())

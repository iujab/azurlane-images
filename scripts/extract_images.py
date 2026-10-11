"""Run azlassets extraction with per-bundle error tolerance.

``azl extract`` runs bundles through a ProcessPoolExecutor and re-raises the
first worker exception, which aborts the whole step: on 2026-10-10 one bundle
Pillow could not encode ("tile cannot extend outside image", bundle 10633 of
12948) threw away every other image of the run. This wrapper swaps the
per-bundle function for one that logs ``SKIP <bundle>: <error>`` to stderr and
returns no images, so the remaining bundles still extract. Skipped bundles are
retried automatically on the next run because they never reach the difflog's
success list.

Usage (same arguments as ``azl extract``):
    python -m scripts.extract_images EN
"""
from __future__ import annotations

import sys

import azlassets.extractor as extractor

_extract_assetbundle = extractor.extract_assetbundle


def extract_assetbundle_tolerant(bpath, targetdir):
    """azlassets.extractor.extract_assetbundle, but a failing bundle is skipped, not fatal."""
    try:
        return _extract_assetbundle(bpath, targetdir)
    except Exception as exc:  # noqa: BLE001 - any per-bundle failure must not kill the pool
        print(f"SKIP {getattr(bpath, 'full', bpath)}: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return []


def install() -> None:
    """Patch the module-level function the process pool resolves by name."""
    extractor.extract_assetbundle = extract_assetbundle_tolerant


def main(argv: list[str] | None = None) -> None:
    import azl  # the azlassets CLI module

    install()
    sys.argv = ["azl", "extract", *(sys.argv[1:] if argv is None else argv)]
    azl.main()


if __name__ == "__main__":
    main()

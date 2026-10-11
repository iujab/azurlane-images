"""The extraction wrapper must swallow a per-bundle failure and keep the pool alive."""
from pathlib import Path
from types import SimpleNamespace

import pytest

azlassets = pytest.importorskip("azlassets")

from scripts import extract_images  # noqa: E402


def test_failing_bundle_is_skipped_not_raised(monkeypatch, capsys):
    def boom(bpath, targetdir):
        raise SystemError("tile cannot extend outside image")

    monkeypatch.setattr(extract_images, "_extract_assetbundle", boom)
    bpath = SimpleNamespace(full=Path("AssetBundles/painting/broken_bundle"))

    assert extract_images.extract_assetbundle_tolerant(bpath, Path("out")) == []
    err = capsys.readouterr().err
    assert "SKIP AssetBundles/painting/broken_bundle: SystemError: tile cannot extend outside image" in err


def test_healthy_bundle_passes_through(monkeypatch):
    monkeypatch.setattr(extract_images, "_extract_assetbundle", lambda bpath, targetdir: [Path("out/a.png")])
    assert extract_images.extract_assetbundle_tolerant(object(), Path("out")) == [Path("out/a.png")]


def test_install_patches_the_name_the_pool_resolves():
    extract_images.install()
    assert azlassets.extractor.extract_assetbundle is extract_images.extract_assetbundle_tolerant

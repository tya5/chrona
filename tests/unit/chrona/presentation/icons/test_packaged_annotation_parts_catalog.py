"""The layered annotation-parts catalogue is separately pinned and reproducible."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import yaml

from chrona import resources
from chrona.presentation.icons.importer import import_theme_assets


ROOT = Path(__file__).resolve().parents[5]
RESOURCE_DIR = ROOT / "src/chrona/resources/icons"
MANIFEST = RESOURCE_DIR / "chrona-annotation-parts-v2026-10-09.manifest"


def _manifest() -> dict:
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))


def test_annotation_parts_catalogue_is_identity_closed_and_regenerable(tmp_path: Path) -> None:
    manifest = _manifest()
    catalog_path = RESOURCE_DIR / manifest["catalog"]["file"]
    source_path = RESOURCE_DIR / manifest["source"]["file"]
    notice_path = RESOURCE_DIR / manifest["license"]["noticeFile"]
    catalog_bytes = catalog_path.read_bytes()
    source_bytes = source_path.read_bytes()
    notice_bytes = notice_path.read_bytes()

    assert sha256(catalog_bytes).hexdigest() == manifest["catalog"]["sha256"]
    assert sha256(source_bytes).hexdigest() == manifest["source"]["sha256"]
    assert sha256(notice_bytes).hexdigest() == manifest["license"]["noticeSha256"]

    catalogue = json.loads(catalog_bytes)
    body = catalogue["body"]
    assert catalogue["version"] == manifest["catalog"]["version"] == "chrona/icon-catalog/v0.5"
    assert catalogue["id"] == "chrona-annotation-parts-v2026-10-09"
    assert body["set"] == manifest["catalog"]["set"] == "chrona-annotation-parts"
    assert body["aliases"] == manifest["catalog"]["aliases"] == ["annotation-parts"]
    assert sorted(body["glyphs"]) == manifest["entries"]["glyphs"] == ["scroll-mounting", "scroll-rods"]
    assert body["patterns"] == manifest["entries"]["patterns"] == {}
    assert body["icons"] == {} and body["entryAliases"] == {}
    assert body["provenance"]["sourceContentIdentity"] == "sha256:" + sha256(source_bytes).hexdigest()
    assert body["provenance"]["license"]["spdx"] == "MIT"
    assert body["provenance"]["license"]["notice"].encode("utf-8") == notice_bytes

    regenerated = tmp_path / catalog_path.name
    result = import_theme_assets(source_path, regenerated)
    assert regenerated.read_bytes() == catalog_bytes
    assert result["contentIdentity"] == "sha256:" + manifest["catalog"]["sha256"]
    assert result["glyphs"] == 2 and result["patterns"] == 0


def test_annotation_parts_are_packaged_and_split_the_existing_scroll_geometry() -> None:
    icons = resources.builtin_preset_source_root("icons")
    manifest = _manifest()
    for name in (
        MANIFEST.name,
        manifest["catalog"]["file"],
        manifest["source"]["file"],
        manifest["license"]["noticeFile"],
    ):
        assert icons.joinpath(name).is_file()

    old_path = ROOT / "docs/archive/resources/icons/chrona-target-parts-v2026-10.yaml"
    old = json.loads(old_path.read_bytes())["body"]["glyphs"]["scroll-frame"]["parts"]
    new = json.loads((RESOURCE_DIR / _manifest()["catalog"]["file"]).read_bytes())["body"]["glyphs"]
    assert new["scroll-mounting"]["viewport"] == new["scroll-rods"]["viewport"] == {"inlineSize": 48, "blockSize": 64}
    assert new["scroll-mounting"]["parts"] == [old[0], old[2]]
    assert new["scroll-rods"]["parts"] == [old[1], old[3], old[4], old[5]]
    for glyph in new.values():
        assert all("color" not in part for part in glyph["parts"])


def test_authored_source_builder_reproduces_committed_source() -> None:
    script = ROOT / "docs/research/presentation/annotation-parts-catalogue-2026-10/build_source.py"
    result = subprocess.run([sys.executable, str(script)], cwd=ROOT, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "source is reproduced exactly" in result.stdout

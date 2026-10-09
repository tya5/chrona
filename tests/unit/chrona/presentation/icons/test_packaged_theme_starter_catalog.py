from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import yaml

from chrona.presentation.icons.importer import import_theme_assets


RESOURCE_DIR = Path(__file__).resolve().parents[5] / "src/chrona/resources/icons"
MANIFEST = RESOURCE_DIR / "chrona-theme-starter-v2026-10-09.manifest"


def test_packaged_theme_starter_catalog_has_pinned_inventory_and_identity(tmp_path: Path) -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    catalog_path = RESOURCE_DIR / manifest["catalog"]["file"]
    source_path = RESOURCE_DIR / manifest["source"]["file"]
    notice_path = RESOURCE_DIR / manifest["license"]["noticeFile"]
    catalog_bytes = catalog_path.read_bytes()
    source_bytes = source_path.read_bytes()
    notice_bytes = notice_path.read_bytes()

    assert sha256(catalog_bytes).hexdigest() == manifest["catalog"]["sha256"]
    assert sha256(source_bytes).hexdigest() == manifest["source"]["sha256"]
    assert sha256(notice_bytes).hexdigest() == manifest["license"]["noticeSha256"]

    catalog = json.loads(catalog_bytes)
    body = catalog["body"]
    assert catalog["version"] == manifest["catalog"]["version"] == "chrona/icon-catalog/v0.5"
    assert catalog["id"] == "chrona-theme-starter-v2026-10-09"
    assert catalog["version"] == manifest["catalog"]["version"]
    assert body["set"] == manifest["catalog"]["set"]
    assert body["aliases"] == manifest["catalog"]["aliases"]
    assert sorted(body["glyphs"]) == manifest["entries"]["glyphs"]
    assert set(body["patterns"]) == set(manifest["entries"]["patterns"])
    for name, expected in manifest["entries"]["patterns"].items():
        assert body["patterns"][name]["densityBasisPoints"] == expected["densityBasisPoints"]

    provenance = body["provenance"]
    assert provenance["sourceContentIdentity"] == "sha256:" + sha256(source_bytes).hexdigest()
    assert provenance["license"]["spdx"] == manifest["license"]["spdx"]
    assert provenance["license"]["notice"].encode("utf-8") == notice_bytes

    regenerated = tmp_path / catalog_path.name
    result = import_theme_assets(source_path, regenerated)
    assert regenerated.read_bytes() == catalog_bytes
    assert result["contentIdentity"] == "sha256:" + manifest["catalog"]["sha256"]
    assert result["glyphs"] == len(manifest["entries"]["glyphs"])
    assert result["patterns"] == len(manifest["entries"]["patterns"])

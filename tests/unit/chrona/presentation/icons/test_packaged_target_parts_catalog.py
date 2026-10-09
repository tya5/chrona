"""The packaged `chrona-target-parts` catalogue (#718) is pinned, regenerable and licensed."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import yaml

from chrona import resources
from chrona.presentation.icons.importer import import_theme_assets


RESOURCE_DIR = Path(__file__).resolve().parents[5] / "src/chrona/resources/icons"
MANIFEST = RESOURCE_DIR / "chrona-target-parts-v2026-10-09.manifest"
STARTER_MANIFEST = RESOURCE_DIR / "chrona-theme-starter-v2026-10-09.manifest"


def _manifest() -> dict:
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))


def test_packaged_target_parts_catalog_has_pinned_inventory_and_identity(tmp_path: Path) -> None:
    manifest = _manifest()
    catalog_path = RESOURCE_DIR / manifest["catalog"]["file"]
    source_path = RESOURCE_DIR / manifest["source"]["file"]
    notice_path = RESOURCE_DIR / manifest["license"]["noticeFile"]
    catalog_bytes, source_bytes, notice_bytes = catalog_path.read_bytes(), source_path.read_bytes(), notice_path.read_bytes()

    assert sha256(catalog_bytes).hexdigest() == manifest["catalog"]["sha256"]
    assert sha256(source_bytes).hexdigest() == manifest["source"]["sha256"]
    assert sha256(notice_bytes).hexdigest() == manifest["license"]["noticeSha256"]

    catalog = json.loads(catalog_bytes)
    body = catalog["body"]
    assert catalog["version"] == manifest["catalog"]["version"] == "chrona/icon-catalog/v0.5"
    assert body["set"] == manifest["catalog"]["set"] == "chrona-target-parts"
    assert body["aliases"] == manifest["catalog"]["aliases"]
    assert sorted(body["glyphs"]) == manifest["entries"]["glyphs"]
    assert set(body["patterns"]) == set(manifest["entries"]["patterns"])
    for name, expected in manifest["entries"]["patterns"].items():
        assert body["patterns"][name]["densityBasisPoints"] == expected["densityBasisPoints"]
    assert body["icons"] == {} and body["entryAliases"] == {}
    seigaiha = body["patterns"]["seigaiha"]
    assert seigaiha["tile"] == {"inlineSize": 20.0, "blockSize": 10.0}
    assert seigaiha["angle"] == 0.0
    assert [(item["cx"], item["cy"], item["radius"], item["fillChannel"], item["strokeWidth"])
            for item in seigaiha["primitives"]] == [
                (cx, cy, radius, channel, 0.8)
                for cx, cy in ((0.0, 10.0), (20.0, 10.0), (10.0, 5.0))
                for radius, channel in ((10.0, "substrate"), (7.0, "none"), (4.0, "none"))]

    provenance = body["provenance"]
    assert provenance["sourceKind"] == "theme-asset-source"
    assert provenance["sourceContentIdentity"] == "sha256:" + sha256(source_bytes).hexdigest()
    assert provenance["license"]["spdx"] == manifest["license"]["spdx"] == "MIT"
    assert provenance["license"]["notice"].encode("utf-8") == notice_bytes

    regenerated = tmp_path / catalog_path.name
    result = import_theme_assets(source_path, regenerated)
    assert regenerated.read_bytes() == catalog_bytes
    assert result["contentIdentity"] == "sha256:" + manifest["catalog"]["sha256"]
    assert result["glyphs"] == len(manifest["entries"]["glyphs"])
    assert result["patterns"] == len(manifest["entries"]["patterns"])


def test_every_entry_has_a_declared_consumer_or_a_named_owner() -> None:
    manifest = _manifest()
    glyphs, patterns = set(manifest["entries"]["glyphs"]), set(manifest["entries"]["patterns"])
    consumers = manifest["consumers"]
    gates, unconsumed = set(consumers["milestone-symbol"]), consumers["none-yet"]
    assert gates | set(unconsumed) == glyphs and not gates & set(unconsumed)
    assert set(consumers["pattern-roles"]) == patterns
    assert glyphs.isdisjoint(patterns)
    assert all(owner.startswith("#") and owner[1:].isdigit() for owner in unconsumed.values())
    assert "seigaiha" in patterns
    assert manifest["entries"]["patterns"]["seigaiha"]["densityBasisPoints"] == 2606


def test_the_catalogue_is_a_wheel_resource_distinct_from_the_pinned_starter() -> None:
    manifest, starter = _manifest(), yaml.safe_load(STARTER_MANIFEST.read_text(encoding="utf-8"))
    icons = resources.builtin_preset_source_root("icons")
    for name in (manifest["catalog"]["file"], manifest["source"]["file"], MANIFEST.name, manifest["license"]["noticeFile"]):
        assert icons.joinpath(name).is_file(), name
    assert manifest["catalog"]["set"] != starter["catalog"]["set"]
    assert not {"chrona-target-parts", "target-parts"} & ({starter["catalog"]["set"]} | set(starter["catalog"]["aliases"]))


def test_parts_carry_no_colour_and_every_stroke_is_complete() -> None:
    body = json.loads((RESOURCE_DIR / _manifest()["catalog"]["file"]).read_bytes())["body"]
    for name, glyph in body["glyphs"].items():
        assert set(glyph) == {"viewport", "parts"}, name
        for part in glyph["parts"]:
            assert part["paint"] in {"fill", "stroke"}
            expected = {"paint", "data"} | ({"strokeWidth", "lineCap", "lineJoin"} if part["paint"] == "stroke" else set())
            assert set(part) == expected, (name, part)
    for name, pattern in body["patterns"].items():
        assert set(pattern) == {"tile", "angle", "densityBasisPoints", "primitives"}, name
        for primitive in pattern["primitives"]:
            assert primitive["kind"] in {"circle", "rect", "path"} and "color" not in primitive
            if primitive["kind"] == "circle" and "fillChannel" in primitive:
                assert primitive["fillChannel"] in {"ink", "substrate", "none"}

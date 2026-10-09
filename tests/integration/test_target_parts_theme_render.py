"""A Theme binds `chrona-target-parts` entries and the product completes them (#718, condition C2)."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys

import yaml

from chrona.app.cli import main
from chrona.presentation.contracts import ClosureIdentity, IconCatalogContract, parse_contract
from chrona.usecases.preset_library import copy_builtin_preset


ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "examples/controller-z/project.yaml"
CATALOGUE = ROOT / "src/chrona/resources/icons/chrona-target-parts-v2026-10-09.yaml"
STARTER_GLYPH = "shape: {catalog: 'chrona-starter:pin'}"
STARTER_PATTERN = "ref: 'chrona-starter:halftone'"


def test_catalogue_parses_as_an_icon_catalog_contract_with_every_entry() -> None:
    payload = CATALOGUE.read_bytes()
    value = yaml.safe_load(payload)
    contract = parse_contract(ClosureIdentity("icon-catalog", value["id"], "packaged", "sha256:" + sha256(payload).hexdigest()), value)
    assert isinstance(contract, IconCatalogContract)
    assert value["body"]["set"] == "chrona-target-parts"
    assert len(value["body"]["glyphs"]) == 17 and len(value["body"]["patterns"]) == 10
    assert value["body"]["patterns"]["seigaiha"]["densityBasisPoints"] == 2606


def test_a_theme_gate_glyph_and_pattern_from_the_catalogue_reach_the_scene_and_the_svg(tmp_path, monkeypatch):
    preset = copy_builtin_preset("technical-print", tmp_path / "copied")
    theme = (preset.parent / "theme.yaml").read_text(encoding="utf-8")
    assert STARTER_GLYPH in theme and STARTER_PATTERN in theme
    theme_path = tmp_path / "theme-target-parts.yaml"
    theme_path.write_text(theme.replace(STARTER_GLYPH, "shape: {catalog: 'chrona-target-parts:lantern'}")
                          .replace(STARTER_PATTERN, "ref: 'chrona-target-parts:hazard-stripes'"), encoding="utf-8")
    svg_path, scene_path = tmp_path / "board.svg", tmp_path / "board.scene.json"
    monkeypatch.setattr(sys, "argv", ["chrona", "render", str(PROJECT), "--preset", str(preset), "--theme", str(theme_path),
                                      "--icon-catalog", str(CATALOGUE), "--output", str(svg_path), "--emit-scene", str(scene_path)])
    main()

    scene = json.loads(scene_path.read_bytes())
    primitives = [item for surface in scene["surfaces"] for item in surface["primitives"]]
    catalogue = json.loads(CATALOGUE.read_bytes())["body"]
    lantern_parts = [item for item in primitives if item.get("kind") == "Symbol" and ":evb-arrival:part:" in item.get("id", "")]
    assert len(lantern_parts) == len(catalogue["glyphs"]["lantern"]["parts"]) == 6
    assert all(item["symbol"]["outline"] and item["paint"] for item in lantern_parts)
    stripes = next(item for item in primitives if item.get("visualRole") == "axis-band-decoration2" and item.get("pattern"))["pattern"]
    expected = catalogue["patterns"]["hazard-stripes"]
    assert (stripes["tileInlineSize"], stripes["tileBlockSize"], stripes["angleDegrees"], stripes["densityBasisPoints"]) == (
        expected["tile"]["inlineSize"], expected["tile"]["blockSize"], expected["angle"], expected["densityBasisPoints"])
    assert b"<pattern " in svg_path.read_bytes()

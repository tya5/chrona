"""Label chips (#428): a background drawn from a label's own measured box."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

from chrona.app.cli import main

ROOT = Path(__file__).resolve().parents[2]


def _primitives(scene: dict) -> dict[str, dict]:
    found: dict[str, dict] = {}

    def walk(value):
        if isinstance(value, dict):
            if isinstance(value.get("id"), str) and "bounds" in value:
                found[value["id"]] = value
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(scene)
    return found


def test_committed_as_of_label_is_a_bare_word_in_a_filled_chip():
    scene = json.loads((ROOT / "examples/halcyon-1/generated/02-programme-board.scene.json").read_text(encoding="utf-8"))
    primitives = _primitives(scene)
    label, chip = primitives["as-of-label"], primitives["chip:as-of-label"]
    assert label["text"] == "Today"
    assert chip["visualRole"] == "as-of-label-chip" and chip["paint"]["fill"]
    assert chip["paintOrder"] < label["paintOrder"]
    text, box = label["bounds"], chip["bounds"]
    inline_pad, block_pad = text["inline"] - box["inline"], text["block"] - box["block"]
    assert inline_pad > 0 and block_pad > 0
    assert box["inlineSize"] == pytest.approx(text["inlineSize"] + 2 * inline_pad)
    assert box["blockSize"] == pytest.approx(text["blockSize"] + 2 * block_pad)
    assert chip["cornerRadius"] == pytest.approx(box["blockSize"] / 2)


def test_a_label_chip_is_not_specific_to_the_as_of_marker(tmp_path, monkeypatch):
    """The same Theme role naming gives member labels chips; no as-of code path is involved."""
    theme = yaml.safe_load((ROOT / "examples/controller-z/themes/executive-light.yaml").read_text(encoding="utf-8"))
    body = theme["body"]
    body["values"]["chip-padding"] = {"type": "number", "value": 0.4}
    body["roles"]["member-label-chip"] = {"backgroundTreatment": "fill", "chipPadding": "chip-padding"}
    body["colorBindings"]["member-label-chip.fill"] = "surfaceRaised"
    theme_path = tmp_path / "theme.yaml"
    theme_path.write_text(yaml.safe_dump(theme, sort_keys=False), encoding="utf-8")
    scene_path = tmp_path / "scene.json"
    monkeypatch.setattr(sys, "argv", [
        "chrona", "render", str(ROOT / "examples/controller-z/project.yaml"),
        "--actual", str(ROOT / "examples/controller-z/actual.yaml"),
        "--view", str(ROOT / "examples/controller-z/views/executive.yaml"), "--theme", str(theme_path),
        "--scheme", str(ROOT / "examples/controller-z/schemes/executive-light.yaml"),
        "--layout", str(ROOT / "examples/controller-z/layouts/executive-review.yaml"),
        "--output", str(tmp_path / "out.svg"), "--emit-scene", str(scene_path),
    ])
    main()
    primitives = _primitives(json.loads(scene_path.read_text(encoding="utf-8")))
    chips = {key: value for key, value in primitives.items() if key.startswith("chip:member-label:")}
    assert chips
    for key, chip in chips.items():
        label = primitives[key.removeprefix("chip:")]["bounds"]
        box = chip["bounds"]
        assert box["inline"] < label["inline"] and box["inline"] + box["inlineSize"] > label["inline"] + label["inlineSize"]
    assert "chip:as-of-label" not in primitives


def test_themes_without_a_chip_role_draw_no_chip():
    for path in sorted(ROOT.glob("examples/*/generated/*.scene.json")):
        primitives = _primitives(json.loads(path.read_text(encoding="utf-8")))
        chips = [key for key in primitives if key.startswith("chip:")]
        if path.parent.parent.name == "halcyon-1" and path.stem.split(".")[0] in {
                "02-programme-board", "04-tvac-slip", "07-replan-baseline", "11-overlay-briefing"}:
            assert chips == ["chip:as-of-label"], path
        else:
            assert chips == [], path

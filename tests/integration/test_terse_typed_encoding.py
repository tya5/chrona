"""Inline typed fields compile and render identically to the resulting YAML Project."""
from __future__ import annotations

import json
import sys
from xml.etree import ElementTree

import yaml

from chrona.app.cli import main
from chrona.resources import default_preset_root


REVISION = "git:0123456789abcdef0123456789abcdef01234567"
VALUES = {"design": "low", "build": "high", "test": "medium"}


def _command(monkeypatch, capsys, *args: str) -> tuple[int, str, str]:
    monkeypatch.setattr(sys, "argv", ["chrona", *args])
    code = 0
    try:
        main()
    except SystemExit as error:
        code = error.code if isinstance(error.code, int) else (0 if error.code is None else 1)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _bar_fills(svg: bytes) -> dict[str, str]:
    root = ElementTree.fromstring(svg)
    found: dict[str, str] = {}
    for element in root.iter():
        scene_id = element.attrib.get("data-scene-id", "")
        if not scene_id.startswith("planned:") or "fill" not in element.attrib:
            continue
        object_id = scene_id.split(":")[1]
        if object_id in VALUES:
            found[object_id] = element.attrib["fill"]
    return found


def test_inline_typed_plan_matches_compile_then_yaml_svg_scene_and_encodes_each_actual_bar(
        tmp_path, monkeypatch, capsys):
    package = {
        "version": "chrona/profile/v0.3",
        "packageId": "team-delivery",
        "requires": {"projectFormat": "timeline/v0.7"},
        "profiles": {"work": {"extends": "task", "fields": {
            "team": {"type": "enum", "enumValues": ["platform", "product"], "required": True},
            "risk": {"type": "enum", "enumValues": ["low", "medium", "high"], "required": True},
        }}},
    }
    (tmp_path / "typed-team.yaml").write_text(yaml.safe_dump(package, sort_keys=False), encoding="utf-8")
    (tmp_path / "typed-plan.chrona").write_text(
        "\n".join((
            "terse 0.1",
            f'project typed-demo "Typed fields demo" calendar office extension team-delivery "typed-team.yaml" {REVISION}',
            "calendar office mon-fri",
            'design "Design" task profile work 5wd from 2026-11-02 risk=low team=platform',
            'build "Build" task profile work 10wd after design risk=high team=platform',
            'test "Test" task profile work 5wd after build risk=medium team=product',
            "",
        )), encoding="utf-8")

    resources = default_preset_root().joinpath("bundles/wallboard-dark")
    view = yaml.safe_load(resources.joinpath("view.yaml").read_bytes())
    view["body"]["colorEncoding"] = {
        "scale": "series", "target": "planned", "source": {"field": "risk"},
        "domain": ["low", "medium", "high"],
    }
    (tmp_path / "risk-view.yaml").write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    code, out, err = _command(monkeypatch, capsys, "compile", "typed-plan.chrona", "--output", "compiled.yaml")
    assert code == 0, (out, err)
    direct = _command(monkeypatch, capsys, "render", "typed-plan.chrona", "--preset", "wallboard-dark",
                      "--view", "risk-view.yaml", "--output", "direct.svg", "--emit-scene", "direct.scene.json")
    assert direct[0] == 0, direct
    compiled = _command(monkeypatch, capsys, "render", "compiled.yaml", "--preset", "wallboard-dark",
                        "--view", "risk-view.yaml", "--output", "compiled.svg", "--emit-scene", "compiled.scene.json")
    assert compiled[0] == 0, compiled

    direct_svg = (tmp_path / "direct.svg").read_bytes()
    compiled_svg = (tmp_path / "compiled.svg").read_bytes()
    assert direct_svg == compiled_svg
    direct_scene_bytes = (tmp_path / "direct.scene.json").read_bytes()
    assert direct_scene_bytes == (tmp_path / "compiled.scene.json").read_bytes()
    direct_scene = json.loads(direct_scene_bytes)
    primitives = {
        item["id"]: item
        for surface in direct_scene["surfaces"] for item in surface["primitives"]
        if item["id"].startswith("planned:")
    }
    svg_fills = _bar_fills(direct_svg)
    assert set(svg_fills) == set(VALUES)
    scene_fills = {}
    for object_id, risk in VALUES.items():
        primitive = next(item for scene_id, item in primitives.items() if scene_id.startswith(f"planned:{object_id}:"))
        assert primitive["encoding"]["field"] == "risk"
        assert primitive["encoding"]["value"] == risk
        scene_fills[object_id] = primitive["paint"]["fill"]
    assert len(set(scene_fills.values())) == len(VALUES)
    assert svg_fills == scene_fills

"""The Wallboard dark catalogue preset: listed, copyable, reproducible by name (#429, I429-4)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

from chrona.app.cli import main
from chrona.resources import safe_load
from chrona.usecases.preset_library import list_builtin_presets
from tests.support.draft_packages import stage_project_package_store

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "src/chrona/resources/presets/bundles/wallboard-dark"
FILES = ("view.yaml", "theme.yaml", "scheme.yaml", "layout.yaml", "detail.yaml")


def _run(monkeypatch, capsys, *argv):
    monkeypatch.setattr(sys, "argv", ["chrona", *argv])
    capsys.readouterr()
    main()
    return capsys.readouterr().out


def _halcyon_store_args(tmp_path: Path) -> tuple[str, str]:
    project_path = ROOT / "examples/halcyon-1/project.yaml"
    project = yaml.safe_load(project_path.read_bytes())
    config = stage_project_package_store(tmp_path / "project-store", project, project_path.parent)
    return "--store-config", str(config)


def test_the_preset_is_listed_and_its_entry_names_only_the_bundle():
    assert "wallboard-dark" in [item["id"] for item in list_builtin_presets()]
    entries = yaml.safe_load((ROOT / "src/chrona/resources/presets/library.yaml").read_text(encoding="utf-8"))["entries"]
    assert [item["id"] for item in entries].count("wallboard-dark") == 1
    members = next(item for item in entries if item["id"] == "wallboard-dark")["members"]
    assert "iconCatalogs" not in members
    for name, member in members.items():
        assert member["sourceRoot"] == "presets/bundles/wallboard-dark"
        assert safe_load((BUNDLE / member["sourcePath"]).read_bytes())["id"] == member["id"], name


def test_the_view_uses_the_generic_vocabulary_for_each_treatment():
    body = safe_load((BUNDLE / "view.yaml").read_bytes())["body"]
    assert body["grouping"] == {"by": "none"}
    assert body["colorEncoding"]["target"] == "planned" and body["colorEncoding"]["domain"] == "firstAppearance"
    assert [column["source"] for column in body["tableColumns"]] == ["path", {"fieldRole": "responsible"}]
    assert "path" in body["visibility"]["labels"]["content"]
    bands = [tier for tier in body["axis"]["tiers"] if tier["role"] == "band"]
    assert [tier["unit"] for tier in bands] == ["quarter", "month"]
    assert bands[0]["fillScale"]["key"] == "alternating"
    assert bands[1]["fillScale"] == {"scale": "axis-month", "key": "alternating", "containingTier": 0}
    theme = safe_load((BUNDLE / "theme.yaml").read_bytes())["body"]
    assert set(theme["colorScales"]["axis-month"]["slots"]) == {"0", "1"}
    assert theme["roles"]["planned"]["markCornerRadius"] == "mark-radius-capsule"


def test_the_scheme_is_a_dark_ground_with_a_darker_tint_per_quarter_hue():
    scheme = safe_load((BUNDLE / "scheme.yaml").read_bytes())["body"]
    assert scheme["suitability"]["background"] == "dark"
    assert int(scheme["colors"]["surface"][1:3], 16) < 0x20


def test_copy_writes_the_bundle_and_render_by_name_equals_the_copy(tmp_path, monkeypatch, capsys):
    copy = tmp_path / "copy"
    assert json.loads(_run(monkeypatch, capsys, "preset", "copy", "wallboard-dark", "--output", str(copy)))["status"] == "ok"
    for filename in FILES:
        assert safe_load((copy / filename).read_bytes()) == safe_load((BUNDLE / filename).read_bytes())
    _run(monkeypatch, capsys, "init", str(tmp_path / "starter"))
    starter = tmp_path / "starter"
    for source, extra in ((starter / "project.yaml", ["--actual", str(starter / "actual.yaml")]),
                          (ROOT / "tests/fixtures/controller-z/project.yaml", [])):
        by_name, by_path = tmp_path / "name.svg", tmp_path / "path.svg"
        assert json.loads(_run(monkeypatch, capsys, "render", str(source), *extra, "--preset", "wallboard-dark",
                               "--output", str(by_name)))["status"] == "ok"
        _run(monkeypatch, capsys, "render", str(source), *extra, "--preset", str(copy / "preset.yaml"), "--output", str(by_path))
        assert by_name.read_bytes() == by_path.read_bytes()


def test_an_existing_example_renders_axis_bands_with_a_fill_per_interval(tmp_path, monkeypatch, capsys):
    scene = tmp_path / "scene.json"
    result = json.loads(_run(
        monkeypatch, capsys, "render", str(ROOT / "examples/halcyon-1/project.yaml"),
        "--actual", str(ROOT / "examples/halcyon-1/actual.yaml"), "--preset", "wallboard-dark",
        *_halcyon_store_args(tmp_path), "--output", str(tmp_path / "h.svg"), "--emit-scene", str(scene)))
    assert result["status"] == "ok" and result["diagnostics"] == []
    assert not [w for w in result["warnings"] if "CONTRAST" in w["code"] or w["code"] == "W_PRESENTATION_SCALE_NOT_SEPARABLE"]
    text = scene.read_text(encoding="utf-8")
    primitives = json.loads(text)["surfaces"][0]["primitives"]
    fills = {item["id"]: item["paint"]["fill"] for item in primitives if item["id"].startswith("axis-band-rect:")}
    quarter = {fill for key, fill in fills.items() if key.startswith("axis-band-rect:0:")}
    month = {fill for key, fill in fills.items() if key.startswith("axis-band-rect:3:")}
    assert len(quarter) == 2 and len(month) == 2 and quarter.isdisjoint(month)

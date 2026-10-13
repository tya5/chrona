"""Synthetic controls for corpus legend/mark Scene checks (#1396)."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from tools import check_legend_keys as checker
from tools.check_legend_keys import legend_key_findings


def _rect(identifier: str, *, fill: str | None = "#B06020", kind: str = "Rect",
          bounds: dict | None = None) -> dict:
    return {"id": identifier, "kind": kind,
            "paint": {"fill": fill, "stroke": None},
            "bounds": bounds or {"inline": 0, "block": 0, "inlineSize": 10, "blockSize": 4}}


def _scene(*surfaces: list[dict]) -> dict:
    return {"surfaces": [{"primitives": primitives} for primitives in surfaces]}


@pytest.mark.parametrize("role", ["planned", "actual", "snapshot", "scenario"])
def test_bar_key_family_and_paint_match(role):
    scene = _scene([_rect(f"{role}:host"), _rect(f"legend-swatch:{role}")])
    assert legend_key_findings(scene) == []


@pytest.mark.parametrize("role", ["planned", "actual", "snapshot", "scenario"])
def test_bar_key_rejects_wrong_shape_family(role):
    scene = _scene([_rect(f"{role}:host"), _rect(f"legend-swatch:{role}", kind="Symbol")])
    assert any(role in finding and "shape" in finding.lower() for finding in legend_key_findings(scene))


@pytest.mark.parametrize("role", ["planned", "actual", "snapshot", "scenario"])
def test_bar_key_rejects_wrong_paint(role):
    scene = _scene([_rect(f"{role}:host"), _rect(f"legend-swatch:{role}", fill=None)])
    assert any(role in finding and "paint" in finding.lower() for finding in legend_key_findings(scene))


def test_milestone_key_matches_the_planned_point_shape_and_paint():
    scene = _scene([_rect("planned:gate", kind="Symbol", fill=None),
                    _rect("legend-swatch:milestone", kind="Symbol", fill=None)])
    assert legend_key_findings(scene) == []

    broken = deepcopy(scene)
    broken["surfaces"][0]["primitives"][1]["kind"] = "Rect"
    findings = legend_key_findings(broken)
    assert any("milestone" in finding and "shape" in finding.lower() for finding in findings)

    broken = deepcopy(scene)
    broken["surfaces"][0]["primitives"][1]["paint"]["fill"] = "#000000"
    findings = legend_key_findings(broken)
    assert any("milestone" in finding and "paint" in finding.lower() for finding in findings)


def test_planned_progress_does_not_require_an_actual_progress_key():
    scene = _scene([
        _rect("planned:campaign"),
        _rect("legend-swatch:planned"),
        _rect("progress-fill:planned:campaign"),
        _rect("legend-swatch:planned:progress-fill"),
        _rect("legend-swatch:actual"),
    ])
    assert legend_key_findings(scene) == []


@pytest.mark.parametrize("role", ["planned", "actual"])
def test_progress_fill_requires_its_owning_role_key_overlay(role):
    scene = _scene([_rect(f"{role}:host"), _rect(f"legend-swatch:{role}"),
                    _rect(f"progress-fill:{role}:host")])
    findings = legend_key_findings(scene)
    assert any(role in finding and "progress" in finding.lower() for finding in findings)


@pytest.mark.parametrize("role", ["planned", "actual"])
def test_progress_overlay_paint_presence_matches_its_hosted_fill(role):
    scene = _scene([_rect(f"{role}:host"), _rect(f"legend-swatch:{role}"),
                    _rect(f"progress-fill:{role}:host", fill="#D09030"),
                    _rect(f"legend-swatch:{role}:progress-fill", fill="#D09030")])
    assert legend_key_findings(scene) == []

    broken = deepcopy(scene)
    broken["surfaces"][0]["primitives"][-1]["paint"]["fill"] = None
    findings = legend_key_findings(broken)
    assert any(role in finding and "progress" in finding.lower() and "paint" in finding.lower()
               for finding in findings)

    broken = deepcopy(scene)
    broken["surfaces"][0]["primitives"][-1]["paint"]["fill"] = "#00AA00"
    findings = legend_key_findings(broken)
    assert any(role in finding and "progress" in finding.lower() and "paint" in finding.lower()
               for finding in findings)


def test_path_key_bounds_must_enclose_its_points():
    path = {"id": "legend-swatch:dependency", "kind": "Path",
            "bounds": {"inline": 0, "block": 0, "inlineSize": 10, "blockSize": 5},
            "points": [[1, 1], [9, 4]]}
    assert legend_key_findings(_scene([path])) == []

    broken = deepcopy(path)
    broken["bounds"]["inlineSize"] = 0
    findings = legend_key_findings(_scene([broken]))
    assert any("dependency" in finding and "enclose" in finding.lower() for finding in findings)


def test_legend_findings_cover_each_surface_not_only_the_first():
    clean = [_rect("planned:host"), _rect("legend-swatch:planned")]
    broken = [_rect("actual:host"), _rect("legend-swatch:actual", kind="Symbol")]
    findings = legend_key_findings(_scene(clean, broken))
    assert any("actual" in finding and "shape" in finding.lower() for finding in findings)


def _write_manifest_scene(root: Path, *, scene_payload: str = '{"surfaces": [{"primitives": []}]}') -> Path:
    deck = root / "examples" / "sample"
    (deck / "generated").mkdir(parents=True)
    (deck / "manifest.yaml").write_text(
        "version: chrona/example-materializer/v0.1\nid: sample\nrole: regression-corpus\n"
        "context: context.yaml\nslides:\n  - id: one\n    context: context.yaml\n"
        "    expectedSvg: generated/one.svg\n    expectedScene: generated/one.scene.json\n",
        encoding="utf-8")
    scene = deck / "generated" / "one.scene.json"
    scene.write_text(scene_payload, encoding="utf-8")
    (deck / "generated" / "orphan.scene.json").write_text(
        '{"surfaces": [{"primitives": []}]}', encoding="utf-8")
    return scene


def test_committed_scene_discovery_uses_manifest_targets_only(tmp_path):
    declared = _write_manifest_scene(tmp_path)

    assert checker.committed_scene_paths(tmp_path) == (declared.resolve(),)


def test_corpus_gate_reports_a_malformed_declared_scene_structurally(tmp_path, monkeypatch, capsys):
    scene = _write_manifest_scene(tmp_path, scene_payload='{"surfaces": [{}]}')
    monkeypatch.setattr(checker, "committed_scene_paths", lambda root=checker.ROOT: (scene,))
    evaluate = checker.evaluate_committed_scenes
    monkeypatch.setattr(checker, "evaluate_committed_scenes",
                        lambda paths, *, root=checker.ROOT: evaluate(paths, root=tmp_path))

    assert checker.main() == 1
    report = json.loads(capsys.readouterr().out)
    assert report["errorCount"] == 1
    assert report["findings"] == [{
        "scene": scene.relative_to(tmp_path).as_posix(),
        "finding": "E_LEGEND_KEY_DOCUMENT:'primitives'",
    }]

"""The bundled appearances declare a `deadline-mark` role, so a View can show deadlines on them (#946).

The ink must read at the mark floor (3:1) on the row ground and on the planned bar; `control-room-dark` has a light bar on a dark
ground, so no single flat ink can, and it keeps asking for the role (a halo is a Layout decision, recorded on the issue).
"""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document
from tests.support import synthetic_review as sr

BUNDLES = Path(__file__).resolve().parents[2] / "src/chrona/resources/presets/bundles"
# `editorial` and the bundled default are mirrored byte for byte under examples/halcyon-1 (reviewer-owned), so they wait for the mirror
PRESETS = ["mission-light", "print-mono", "executive-light", "elevated-light", "technical-print"]


def _source() -> dict:
    source = sr.project({"a": sr.span("a", date(2026, 10, 1), 20), "b": sr.span("b", date(2026, 10, 5), 20, owner="b")})
    source["objects"]["a"]["deadline"] = "2026-10-10"
    source["objects"]["b"]["deadline"] = "2026-10-12"
    return source


def _project(tmp_path: Path) -> None:
    (tmp_path / "project.yaml").write_text(
        yaml.safe_dump(json.loads(json.dumps(_source(), default=lambda value: value.isoformat()))), encoding="utf-8")


def _render(tmp_path: Path, name: str, *files: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", "from chrona.app.cli import main; main()", "render", "project.yaml", *files, "--output", f"{name}.svg",
         "--emit-scene", f"{name}.scene.json"], cwd=tmp_path, capture_output=True, text=True, timeout=300)


def _deadline_findings(tmp_path: Path, name: str) -> list:
    document = json.loads((tmp_path / f"{name}.scene.json").read_text(encoding="utf-8"))
    assert any(item.get("purpose") == "deadline-mark" for item in document["surfaces"][0]["primitives"])
    return [item for item in evaluate_scene_contrast(document) if item.visual_role == "deadline-mark"]


def _show_deadlines(path: Path) -> None:
    view = yaml.safe_load(path.read_text(encoding="utf-8"))
    view["body"]["deadlines"] = {"show": "all"}
    path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")


@pytest.mark.parametrize("preset", PRESETS)
def test_a_view_that_shows_deadlines_renders_on_a_bundled_appearance_and_every_mark_is_visible(tmp_path, preset):
    _project(tmp_path)
    copied = subprocess.run([sys.executable, "-c", "from chrona.app.cli import main; main()", "preset", "copy", preset, "--output", "look"],
                            cwd=tmp_path, capture_output=True, text=True, timeout=120)
    assert copied.returncode == 0, copied.stdout
    _show_deadlines(tmp_path / "look/view.yaml")
    profile = ["--visual-profile", "chrona-output/visual/v0.7-svg"] if preset in {"elevated-light", "technical-print"} else []

    result = _render(tmp_path, "out", "--preset", "look/preset.yaml", *profile)

    assert result.returncode == 0, result.stdout
    findings = _deadline_findings(tmp_path, "out")
    assert findings and all(item.severity != "error" and item.contrast_ratio >= 3.0 for item in findings), preset


def test_control_room_dark_still_asks_for_the_role(tmp_path):
    parts = sr.bundle("control-room-dark")
    parts["view"]["body"]["deadlines"] = {"show": "all"}

    with pytest.raises(Exception) as raised:
        sr.render(tmp_path, _source(), presentation=parts)
    assert getattr(raised.value, "code", "") == "E_THEME_ROLE_REQUIRED" or "deadline-mark" in str(raised.value)

"""Legend keys agree with the marks they name (#499): fill and stroke, shape family, landscape bars, the progress fill, relation bounds.

The bundled default and the presets that ship a legend are rendered fresh from the HALCYON-1 Project and Actual Set (read only),
so the committed generated evidence does not take part.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tests.support.legend_keys import legend_key_findings

ROOT = Path(__file__).resolve().parents[2]


def _scene(tmp_path: Path, *preset: str) -> dict:
    output = tmp_path / "scene.json"
    result = subprocess.run(
        [sys.executable, "-c", "from chrona.app.cli import main; main()", "render", str(ROOT / "examples/halcyon-1/project.yaml"),
         "--actual", str(ROOT / "examples/halcyon-1/actual.yaml"), "--output", str(tmp_path / "out.svg"), "--emit-scene", str(output), *preset],
        cwd=tmp_path, capture_output=True, text=True, timeout=600)
    assert result.returncode == 0, result.stdout
    return json.loads(output.read_text(encoding="utf-8"))


@pytest.mark.parametrize("preset", [(), ("--preset", "editorial"), ("--preset", "executive-light"), ("--preset", "technical-print", "--visual-profile", "chrona-output/visual/v0.7-svg")])
def test_every_legend_key_agrees_with_its_marks(tmp_path, preset):
    document = _scene(tmp_path, *preset)

    keys = [item["id"] for item in document["surfaces"][0]["primitives"] if item["id"].startswith("legend-swatch:")]
    assert "legend-swatch:planned" in keys  # the legend is there to be checked
    assert legend_key_findings(document) == []


def test_the_bundled_default_keys_are_the_ones_the_issue_asked_for(tmp_path):
    items = {item["id"]: item for item in _scene(tmp_path)["surfaces"][0]["primitives"]}

    milestone, planned = items["legend-swatch:milestone"], items["legend-swatch:planned"]
    assert milestone["kind"] == "Symbol" and milestone["paint"].get("fill") is None and milestone["paint"].get("stroke") is not None  # hollow
    assert planned["bounds"]["inlineSize"] > planned["bounds"]["blockSize"]  # a horizontal capsule
    progress = items["legend-swatch:actual:progress-fill"]
    assert progress["paint"].get("fill") == next(item for key, item in items.items() if key.startswith("progress-fill:"))["paint"].get("fill") is not None
    for role in ("dependency", "asOf"):
        key = items[f"legend-swatch:{role}"]
        assert key["bounds"]["inlineSize"] > 0 and key["bounds"]["blockSize"] > 0


def test_planned_progress_has_its_plan_key_not_an_actual_key(tmp_path):
    example = ROOT / "examples/halcyon-1"
    document = _scene(tmp_path,
        "--view", str(example / "views/02-programme-board.yaml"),
        "--theme", str(example / "themes/wallboard.yaml"),
        "--scheme", str(example / "schemes/control-room-dark.yaml"),
        "--layout", str(example / "layouts/wallboard-programme-board.yaml"),
        "--summary", str(example / "profiles/summary-countdown.yaml"),
        "--detail", str(example / "profiles/detail.yaml"),
        "--viewport", "1920x1080", "--visual-profile", "chrona-output/visual/v0.7-svg")
    items = {item["id"]: item for item in document["surfaces"][0]["primitives"]}
    fills = [item for identity, item in items.items() if identity.startswith("progress-fill:planned:")]
    assert fills
    assert items["legend-swatch:planned:progress-fill"]["paint"] == fills[0]["paint"]
    assert "legend-swatch:actual:progress-fill" not in items
    assert legend_key_findings(document) == []
    broken = deepcopy(document)
    broken["surfaces"][0]["primitives"] = [item for item in broken["surfaces"][0]["primitives"]
                                             if item["id"] != "legend-swatch:planned:progress-fill"]
    assert any("planned" in finding and "progress" in finding for finding in legend_key_findings(broken))


def test_the_check_reports_each_kind_of_disagreement(tmp_path):
    document = _scene(tmp_path)
    primitives = {item["id"]: item for item in document["surfaces"][0]["primitives"]}

    def broken(**changes) -> list[str]:
        copy = deepcopy(document)
        by_id = {item["id"]: item for item in copy["surfaces"][0]["primitives"]}
        for identifier, change in changes.items():
            change(by_id[identifier])
        return legend_key_findings(copy)

    assert any("fill/stroke" in item for item in broken(**{"legend-swatch:milestone": lambda i: i["paint"].update(fill="#000000")}))
    assert any("landscape" in item for item in broken(**{"legend-swatch:planned": lambda i: i["bounds"].update(inlineSize=9.6)}))
    assert any("enclose" in item for item in broken(**{"legend-swatch:dependency": lambda i: i["bounds"].update(inlineSize=0, blockSize=0)}))
    copy = deepcopy(document)
    copy["surfaces"][0]["primitives"] = [item for item in copy["surfaces"][0]["primitives"] if item["id"] != "legend-swatch:actual:progress-fill"]
    assert any("Progress key shows none" in item for item in legend_key_findings(copy))
    assert primitives  # the rendered scene is the one under test

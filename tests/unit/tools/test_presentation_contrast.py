from __future__ import annotations

import json

from tools.presentation_contrast import evaluate_committed_scenes, render_markdown, report_document


def _scene(*primitives):
    return {"version": "chrona/scene/v0.6", "kind": "scene", "surfaces": [{
        "id": "review", "canvasPaint": {"fill": "#FFFFFF", "opacity": 1}, "primitives": list(primitives),
    }]}


def test_report_aggregates_per_purpose_and_retains_all_policy_errors(tmp_path):
    path = tmp_path / "examples/demo/generated/slide.scene.json"
    path.parent.mkdir(parents=True)
    primitive = {"id": "band", "visualRole": "row-band", "purpose": "row-decoration",
                 "paint": {"fill": "#FFFFFF", "opacity": 1}}
    path.write_text(json.dumps(_scene(primitive)), encoding="utf-8")

    report = report_document(evaluate_committed_scenes((path,), root=tmp_path))

    assert report["errorCount"] == 2
    assert report["rows"][0]["purpose"] == "row-decoration"
    assert report["rows"][0]["minimumContrast"] == 1
    assert report["corpusErrors"] == ["E_PRESENTATION_CONTRAST_DECORATION_WITNESS"]
    assert "`row-band`" in render_markdown(report)

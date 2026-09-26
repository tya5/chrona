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


def test_report_names_measured_primitive_ground_and_channel(tmp_path):
    path = tmp_path / "examples/demo/generated/slide.scene.json"
    path.parent.mkdir(parents=True)
    host = {"id": "host", "kind": "Rect", "bounds": {
        "inline": 0, "block": 0, "inlineSize": 100, "blockSize": 20,
    }, "paint": {"fill": "#FFFFFF", "opacity": 1}}
    mark = {"id": "planned", "kind": "Rect", "visualRole": "planned",
            "purpose": "task-state", "bounds": {
                "inline": 10, "block": 5, "inlineSize": 30, "blockSize": 10,
            }, "paint": {"fill": "#000000", "opacity": 1}}
    path.write_text(json.dumps(_scene(host, mark)), encoding="utf-8")

    report = report_document(evaluate_committed_scenes((path,), root=tmp_path))
    finding = next(item["finding"] for item in report["findings"]
                   if item["finding"]["primitiveId"] == "planned")

    assert finding["groundId"] == "host"
    assert finding["groundKind"] == "flat"
    assert finding["groundColor"] == "#FFFFFF"
    assert finding["paintChannel"] == "fill"
    assert "`planned` | `planned` | 25.000, 10.000 | `host` | flat | `#FFFFFF` | fill" in render_markdown(report)

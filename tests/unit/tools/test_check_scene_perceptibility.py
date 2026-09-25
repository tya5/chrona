from __future__ import annotations

import json

from tools.check_scene_perceptibility import evaluate_committed_scenes, report_document, render_human


def _scene(*primitives):
    return {"version": "chrona/scene/v0.6", "kind": "scene", "surfaces": [{"id": "review", "slots": [
        {"id": "slot", "bounds": {"inline": 0, "block": 0, "inlineSize": 10, "blockSize": 10}, "overflow": "visible-overflow"},
    ], "canvasPaint": {"fill": "#FFFFFF", "opacity": 1}, "primitives": list(primitives)}]}


def _text(identifier, inline_size=10):
    return {"id": identifier, "kind": "Text", "slotId": "slot", "bounds": {
        "inline": 0, "block": 0, "inlineSize": inline_size, "blockSize": 10}, "paintOrder": 0}


def test_tool_reports_each_declared_overflow_and_machine_transport(tmp_path):
    path = tmp_path / "examples/demo/generated/slide.scene.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(_scene(_text("text", 11))), encoding="utf-8")

    report = report_document(evaluate_committed_scenes((path,), root=tmp_path))

    assert report["errorCount"] == 0
    assert report["findings"][0]["scene"] == "examples/demo/generated/slide.scene.json"
    assert report["findings"][0]["finding"]["code"] == "I_SCENE_DECLARED_VISIBLE_OVERFLOW"
    assert "disposition=visible-overflow" in render_human(report)


def test_tool_turns_invalid_or_error_scene_into_named_failure_record(tmp_path):
    path = tmp_path / "examples/demo/generated/slide.scene.json"
    path.parent.mkdir(parents=True)
    path.write_text("not json", encoding="utf-8")

    report = report_document(evaluate_committed_scenes((path,), root=tmp_path))

    assert report["errorCount"] == 1
    assert report["findings"][0]["finding"]["code"] == "E_SCENE_PERCEPTIBILITY_DOCUMENT"

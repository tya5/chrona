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

    # The invisible band is a warning (#995); only the missing corpus witness is an error.
    assert report["errorCount"] == 1
    assert report["warningCount"] == 1
    assert report["rows"][0]["purpose"] == "row-decoration"
    assert report["rows"][0]["minimumContrast"] == 1
    assert (report["rows"][0]["errorCount"], report["rows"][0]["warningCount"]) == (0, 1)
    assert report["corpusErrors"] == ["E_PRESENTATION_CONTRAST_DECORATION_WITNESS"]
    assert "`row-band`" in render_markdown(report)
    assert "## Decoration corpus witness" in render_markdown(report)


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


# --- #995: a decoration warns, text and marks fail --------------------------------------------------------


def _corpus(tmp_path, monkeypatch, *extra):
    """A committed Scene that paints every decoration role (the first one faint) plus `extra` primitives."""
    from chrona.presentation.model.semantic_registry import ContrastClass, contrast_bindings
    from tools import presentation_contrast

    decorations = []
    for number, binding in enumerate(contrast_bindings(ContrastClass.DECORATION)):
        fill = "#F4F4F4" if number == 0 else "#202020"
        decorations.append({"id": f"d{number}", "kind": "Rect", "visualRole": binding.scene_role,
                            "purpose": binding.purpose, "paintOrder": 10,
                            "bounds": {"inline": 200 + number * 30, "block": 0, "inlineSize": 20, "blockSize": 10},
                            "paint": {"fill": fill, "opacity": 1}})
    path = tmp_path / "examples/demo/generated/slide.scene.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(_scene(*decorations, *extra)), encoding="utf-8")
    monkeypatch.setattr(presentation_contrast, "committed_scene_paths", lambda root: (path,))
    return presentation_contrast


def test_a_corpus_with_only_a_warned_decoration_passes_the_check(tmp_path, monkeypatch):
    tool = _corpus(tmp_path, monkeypatch)
    output = tmp_path / "report.md"
    assert tool.main(("--root", str(tmp_path), "--output", str(output))) == 0
    assert tool.main(("--root", str(tmp_path), "--output", str(output), "--check")) == 0
    text = output.read_text(encoding="utf-8")
    assert "warnings: 1." in text and "errors: 0;" in text
    assert "| Errors | Warnings |" in text and "| warning |" in text


def test_a_corpus_with_an_illegible_mark_still_fails_the_check(tmp_path, monkeypatch):
    mark = {"id": "planned", "kind": "Rect", "visualRole": "planned", "purpose": "planned", "paintOrder": 100,
            "bounds": {"inline": 10, "block": 5, "inlineSize": 30, "blockSize": 10},
            "paint": {"fill": "#FFFFFF", "opacity": 1}}
    tool = _corpus(tmp_path, monkeypatch, mark)
    output = tmp_path / "report.md"
    assert tool.main(("--root", str(tmp_path), "--output", str(output))) == 1
    assert tool.main(("--root", str(tmp_path), "--output", str(output), "--check")) == 1
    assert "errors: 1;" in output.read_text(encoding="utf-8")


def test_a_corpus_with_illegible_text_still_fails_the_check(tmp_path, monkeypatch):
    text = {"id": "cell", "kind": "Text", "visualRole": "variance-ahead", "purpose": "table-cell",
            "paintOrder": 300, "contrastTreatment": "required",
            "bounds": {"inline": 10, "block": 5, "inlineSize": 30, "blockSize": 10},
            "paint": {"fill": "#FFFFFF", "opacity": 1}}
    tool = _corpus(tmp_path, monkeypatch, text)
    assert tool.main(("--root", str(tmp_path), "--output", str(tmp_path / "report.md"))) == 1

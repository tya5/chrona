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


def _corpus(tmp_path, monkeypatch, *extra, listed=True, omit_roles=()):
    """A committed Scene that paints every decoration role (the first one faint) plus `extra` primitives.

    Its Theme is `demo`; the repository's opt-in registry (#1126) lists it unless `listed` is false.
    """
    from chrona.presentation.model.semantic_registry import ContrastClass, contrast_bindings
    from tools import presentation_contrast

    decorations = []
    selected = [binding for binding in contrast_bindings(ContrastClass.DECORATION)
                if binding.scene_role not in omit_roles]
    for number, binding in enumerate(selected):
        fill = "#F4F4F4" if number == 0 else "#202020"
        if binding.scene_role == "row-rule":
            decorations.append({"id": f"d{number}", "kind": "Path", "visualRole": binding.scene_role,
                                "purpose": binding.purpose, "paintOrder": 10,
                                "points": [[200 + number * 30, 0], [220 + number * 30, 0]],
                                "paint": {"stroke": fill, "strokeWidth": 0.5, "opacity": 1}})
        else:
            decorations.append({"id": f"d{number}", "kind": "Rect", "visualRole": binding.scene_role,
                                "purpose": binding.purpose, "paintOrder": 10,
                                "bounds": {"inline": 200 + number * 30, "block": 0,
                                           "inlineSize": 20, "blockSize": 10},
                                "paint": {"fill": fill, "opacity": 1}})
    path = tmp_path / "examples/demo/generated/slide.scene.json"
    path.parent.mkdir(parents=True)
    document = _scene(*decorations, *extra)
    document["provenance"] = {"resources": [{"kind": "theme", "id": "demo", "revision": "r", "contentIdentity": "x"}]}
    path.write_text(json.dumps(document), encoding="utf-8")
    registry = tmp_path / "conformance/contrast-opt-in.yaml"
    registry.parent.mkdir(parents=True)
    registry.write_text("version: chrona/contrast-opt-in/v0.1\nthemes:\n" + ("  - demo\n" if listed else "  - other\n"),
                        encoding="utf-8")
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


def test_each_row_decoration_alternative_satisfies_coverage_without_ignoring_findings(tmp_path, monkeypatch):
    from tools import presentation_contrast

    for omitted, present in (({"row-rule"}, "row-band"), ({"row-band"}, "row-rule")):
        case_root = tmp_path / present
        tool = _corpus(case_root, monkeypatch, omit_roles=omitted)
        records = tool.evaluate_committed_scenes(tool.committed_scene_paths(case_root), root=case_root)
        report = tool.report_document(records)

        assert report["corpusErrors"] == []
        finding_roles = {item["finding"]["visualRole"] for item in records}
        assert present in finding_roles
        assert omitted.isdisjoint(finding_roles)


def test_absent_both_row_decoration_alternatives_is_a_coverage_error(tmp_path, monkeypatch):
    tool = _corpus(tmp_path, monkeypatch, omit_roles={"row-band", "row-rule"})

    report = tool.report_document(tool.evaluate_committed_scenes(
        tool.committed_scene_paths(tmp_path), root=tmp_path))

    assert report["corpusErrors"] == ["E_PRESENTATION_CONTRAST_DECORATION_WITNESS"]


def test_row_alternative_does_not_waive_an_unrelated_decoration_role(tmp_path, monkeypatch):
    tool = _corpus(tmp_path, monkeypatch, omit_roles={"axis-band-decoration"})

    report = tool.report_document(tool.evaluate_committed_scenes(
        tool.committed_scene_paths(tmp_path), root=tmp_path))

    assert report["corpusErrors"] == ["E_PRESENTATION_CONTRAST_DECORATION_WITNESS"]


def test_a_corpus_with_an_illegible_mark_still_fails_the_check(tmp_path, monkeypatch):
    mark = {"id": "planned", "kind": "Rect", "visualRole": "planned", "purpose": "planned", "paintOrder": 100,
            "bounds": {"inline": 10, "block": 5, "inlineSize": 30, "blockSize": 10},
            "paint": {"fill": "#FFFFFF", "opacity": 1}}
    tool = _corpus(tmp_path, monkeypatch, mark)
    output = tmp_path / "report.md"
    assert tool.main(("--root", str(tmp_path), "--output", str(output))) == 1
    assert tool.main(("--root", str(tmp_path), "--output", str(output), "--check")) == 1
    assert "errors: 1;" in output.read_text(encoding="utf-8")


_ILLEGIBLE_MARK = {"id": "planned", "kind": "Rect", "visualRole": "planned", "purpose": "planned", "paintOrder": 100,
                   "bounds": {"inline": 10, "block": 5, "inlineSize": 30, "blockSize": 10},
                   "paint": {"fill": "#FFFFFF", "opacity": 1}}
_ILLEGIBLE_TEXT = {"id": "cell", "kind": "Text", "visualRole": "variance-ahead", "purpose": "table-cell",
                   "paintOrder": 300, "contrastTreatment": "required",
                   "bounds": {"inline": 10, "block": 5, "inlineSize": 30, "blockSize": 10},
                   "paint": {"fill": "#FFFFFF", "opacity": 1}}


def test_a_theme_the_repository_has_not_opted_in_only_warns_on_a_mark_and_on_text(tmp_path, monkeypatch):
    tool = _corpus(tmp_path, monkeypatch, _ILLEGIBLE_MARK, _ILLEGIBLE_TEXT, listed=False)
    output = tmp_path / "report.md"
    assert tool.main(("--root", str(tmp_path), "--output", str(output))) == 0
    assert tool.main(("--root", str(tmp_path), "--output", str(output), "--check")) == 0
    text = output.read_text(encoding="utf-8")
    assert "errors: 0;" in text and "warnings: 3." in text
    assert "## Themes not opted in" in text and "| `demo` | 1 | 3 | 0 |" in text


def test_the_opt_in_registry_is_what_holds_a_theme_to_the_floors(tmp_path, monkeypatch):
    # The same Scene, the same findings: only the registry decides whether they are errors.
    tool = _corpus(tmp_path, monkeypatch, _ILLEGIBLE_MARK, _ILLEGIBLE_TEXT, listed=True)
    assert tool.main(("--root", str(tmp_path), "--output", str(tmp_path / "report.md"))) == 1
    assert "| Themes not opted in" not in (tmp_path / "report.md").read_text(encoding="utf-8")
    (tmp_path / "conformance/contrast-opt-in.yaml").unlink()
    assert tool.main(("--root", str(tmp_path), "--output", str(tmp_path / "report.md"))) == 0


def test_a_scene_without_a_theme_in_its_provenance_is_not_opted_in(tmp_path, monkeypatch):
    tool = _corpus(tmp_path, monkeypatch, _ILLEGIBLE_MARK)
    path = tmp_path / "examples/demo/generated/slide.scene.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    del document["provenance"]
    path.write_text(json.dumps(document), encoding="utf-8")
    assert tool.main(("--root", str(tmp_path), "--output", str(tmp_path / "report.md"))) == 0
    assert "(no Theme in provenance)" in (tmp_path / "report.md").read_text(encoding="utf-8")


def test_a_corpus_with_illegible_text_still_fails_the_check(tmp_path, monkeypatch):
    text = {"id": "cell", "kind": "Text", "visualRole": "variance-ahead", "purpose": "table-cell",
            "paintOrder": 300, "contrastTreatment": "required",
            "bounds": {"inline": 10, "block": 5, "inlineSize": 30, "blockSize": 10},
            "paint": {"fill": "#FFFFFF", "opacity": 1}}
    tool = _corpus(tmp_path, monkeypatch, text)
    assert tool.main(("--root", str(tmp_path), "--output", str(tmp_path / "report.md"))) == 1

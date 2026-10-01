"""#497: the legend-truncation gate, proven on synthetic Scene documents (no `examples/` input)."""
from __future__ import annotations

import json

from tools.check_legend_truncation import (
    configure_stdout, evaluate_committed_scenes, evaluate_scene, render_human, report_document,
)

ELLIPSIS = "…"


def _text(identifier: str, text: str, *, kind: str = "Text") -> dict:
    return {"id": identifier, "kind": kind, "text": text, "textLayout": {"lines": [text]}}


def _diagnostic(identifier: str) -> str:
    identity = {"failureKind": "legend-text", "placementId": identifier, "sourceRef": identifier.removeprefix("legend:")}
    return "W_LAYOUT_TEXT_ELLIPSIZED:" + json.dumps(identity, separators=(",", ":"), sort_keys=True)


def _warning(identifier: str, required: float, available: float, *, code: str = "W_LAYOUT_TEXT_ELLIPSIZED") -> dict:
    return {"code": code, "placementId": identifier, "requiredInline": required, "availableInline": available}


def _scene(primitives, *, diagnostics=(), warnings=()) -> dict:
    surface = {"id": "review", "primitives": list(primitives)}
    if warnings:
        surface["fitWarnings"] = list(warnings)
    return {"version": "chrona/scene/v0.6", "kind": "scene", "surfaces": [surface], "diagnostics": list(diagnostics)}


def _codes(document) -> list[tuple[str, str]]:
    return [(item["code"], item["primitiveId"]) for item in evaluate_scene(document)]


def test_a_truncated_legend_text_with_its_diagnostic_and_facts_passes():
    document = _scene([_text("legend:a", "Spac" + ELLIPSIS)], diagnostics=[_diagnostic("legend:a")],
                      warnings=[_warning("legend:a", 90.0, 40.0)])

    assert _codes(document) == []


def test_a_truncated_legend_text_without_the_diagnostic_fails():
    document = _scene([_text("legend:a", "Spac" + ELLIPSIS)], warnings=[_warning("legend:a", 90.0, 40.0)])

    assert _codes(document) == [("E_LEGEND_TRUNCATION_UNREPORTED", "legend:a")]


def test_a_diagnostic_for_another_primitive_does_not_cover_this_one():
    document = _scene([_text("legend:a", "Spac" + ELLIPSIS), _text("legend:b", "Plan")],
                      diagnostics=[_diagnostic("legend:b")], warnings=[_warning("legend:b", 90.0, 40.0)])

    assert _codes(document) == [("E_LEGEND_TRUNCATION_UNREPORTED", "legend:a")]


def test_a_diagnostic_without_facts_or_with_facts_that_do_not_show_a_shortage_fails():
    missing = _scene([_text("legend:a", "Spac" + ELLIPSIS)], diagnostics=[_diagnostic("legend:a")])
    equal = _scene([_text("legend:a", "Spac" + ELLIPSIS)], diagnostics=[_diagnostic("legend:a")],
                   warnings=[_warning("legend:a", 40.0, 40.0)])
    other_code = _scene([_text("legend:a", "Spac" + ELLIPSIS)], diagnostics=[_diagnostic("legend:a")],
                        warnings=[_warning("legend:a", 90.0, 40.0, code="W_LAYOUT_VISIBLE_OVERFLOW")])

    for document in (missing, equal, other_code):
        assert _codes(document) == [("E_LEGEND_TRUNCATION_FACTS", "legend:a")]


def test_a_legend_without_an_ellipsis_passes_with_or_without_diagnostics():
    assert _codes(_scene([_text("legend:a", "Spacecraft bus"), _text("legend:b", "Actual")])) == []


def test_an_ellipsis_in_other_texts_is_not_a_legend_truncation():
    document = _scene([_text("note:a", "Long note" + ELLIPSIS), _text("legend-swatch:a", "x" + ELLIPSIS),
                       _text("legend:a", "Plan" + ELLIPSIS, kind="Rect")])

    assert _codes(document) == []


def test_an_ellipsis_only_in_the_laid_out_lines_still_counts():
    primitive = {"id": "legend:a", "kind": "Text", "text": "Spacecraft bus",
                 "textLayout": {"lines": ["Spac" + ELLIPSIS]}}

    assert _codes(_scene([primitive])) == [("E_LEGEND_TRUNCATION_UNREPORTED", "legend:a")]


def test_an_ellipsis_only_in_the_text_field_still_counts():
    primitive = {"id": "legend:a", "kind": "Text", "text": "Spac" + ELLIPSIS, "textLayout": {"lines": ["Spacecraft bus"]}}

    assert _codes(_scene([primitive])) == [("E_LEGEND_TRUNCATION_UNREPORTED", "legend:a")]


def test_a_malformed_diagnostic_payload_is_not_a_report():
    document = _scene([_text("legend:a", "Spac" + ELLIPSIS)],
                      diagnostics=["W_LAYOUT_TEXT_ELLIPSIZED:not json", "W_LAYOUT_TEXT_ELLIPSIZED:[1]"],
                      warnings=[_warning("legend:a", 90.0, 40.0)])

    assert _codes(document) == [("E_LEGEND_TRUNCATION_UNREPORTED", "legend:a")]


def test_every_truncated_text_is_reported_once_each():
    document = _scene([_text("legend:a", "A" + ELLIPSIS), _text("legend:b", "B" + ELLIPSIS)])

    assert _codes(document) == [("E_LEGEND_TRUNCATION_UNREPORTED", "legend:a"),
                                ("E_LEGEND_TRUNCATION_UNREPORTED", "legend:b")]


def test_the_tool_reports_scene_paths_and_names_an_unreadable_scene(tmp_path):
    good = tmp_path / "examples/demo/generated/good.scene.json"
    bad = tmp_path / "examples/demo/generated/bad.scene.json"
    broken = tmp_path / "examples/demo/generated/broken.scene.json"
    good.parent.mkdir(parents=True)
    good.write_text(json.dumps(_scene([_text("legend:a", "Plan")])), encoding="utf-8")
    bad.write_text(json.dumps(_scene([_text("legend:a", "Spac" + ELLIPSIS)])), encoding="utf-8")
    broken.write_text("not json", encoding="utf-8")

    report = report_document(evaluate_committed_scenes((good, bad, broken), root=tmp_path))

    assert report["errorCount"] == 2
    assert [(item["scene"].rsplit("/", 1)[1], item["finding"]["code"]) for item in report["findings"]] == [
        ("bad.scene.json", "E_LEGEND_TRUNCATION_UNREPORTED"), ("broken.scene.json", "E_LEGEND_TRUNCATION_DOCUMENT")]
    text = render_human(report)
    assert "E_LEGEND_TRUNCATION_UNREPORTED examples/demo/generated/bad.scene.json primitive=legend:a" in text
    assert text.endswith("Legend truncation: FAIL (2 errors)")


def test_a_clean_corpus_prints_pass(tmp_path):
    assert render_human(report_document(())) == "Legend truncation: PASS (0 errors)"


def test_report_transport_is_utf8():
    calls = []

    class Stream:
        def reconfigure(self, **kwargs):
            calls.append(kwargs)

    configure_stdout(Stream())

    assert calls == [{"encoding": "utf-8"}]

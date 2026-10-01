import json

import pytest
import yaml

from chrona.core.diagnostics import Diagnostic
from chrona.core.ports import SnapshotReadError
from chrona.presentation.contracts import PresentationIngressRejected
from chrona.presentation.contracts.diagnostics import PresentationDiagnostic
from chrona.presentation.fonts.importer import FontImportError
from chrona.presentation.icons.importer import IconImportError
from chrona.presentation.model.closure import ClosureError
from chrona.usecases.failure_report import StableFailure, collapse_records, rejection_report, report_failure
from chrona.usecases.render_review import RenderFailed, RenderRejected


def _one(report):
    assert len(report.diagnostics) == 1
    return report.diagnostics[0]


def test_a_stable_failure_keeps_its_fields_key_order_and_exit_code():
    report = report_failure(StableFailure("E_X", "msg", "cli", "/output", 2))
    assert (report.status, report.exit_code) == ("failed", 2)
    assert list(_one(report)) == ["code", "severity", "component", "sourceRef", "revisionRefs", "message"]
    assert _one(report) == {"code": "E_X", "severity": "error", "component": "cli", "sourceRef": "/output",
                            "revisionRefs": [], "message": "msg"}
    assert list(report.payload()) == ["status", "diagnostics"]
    assert report_failure(StableFailure("E_X", "msg")).status == "rejected"


@pytest.mark.parametrize(("error", "status", "code", "component", "exit_code"), [
    (SnapshotReadError("E_STORE_REFERENCE", "gone"), "rejected", "E_STORE_REFERENCE", "closure", 1),
    (ClosureError("E_CLOSURE_KIND", "/x", "bad"), "rejected", "E_CLOSURE_KIND", "closure", 1),
    (IconImportError("E_ICON_X"), "rejected", "E_ICON_X", "icon-import", 1),
    (FontImportError("E_FONT_X"), "rejected", "E_FONT_X", "font-import", 1),
    (json.JSONDecodeError("bad", "{", 1), "failed", "E_INPUT_JSON", "cli", 2),
    (yaml.YAMLError("bad"), "failed", "E_INPUT_YAML", "cli", 2),
    (FileNotFoundError(2, "No such file", "x"), "failed", "E_INPUT_IO", "cli", 2),
    (ValueError("E_COMING_FROM_A_RULE"), "rejected", "E_COMING_FROM_A_RULE", "presentation", 1),
    (ValueError("something else"), "rejected", "E_PRESENTATION_REJECTED", "presentation", 1),
    (RuntimeError("boom"), "failed", "E_TOOL_FAILURE", "cli", 2),
])
def test_the_exception_ladder(error, status, code, component, exit_code):
    report = report_failure(error)
    assert (report.status, _one(report)["code"], _one(report)["component"], report.exit_code) == (
        status, code, component, exit_code)


def test_a_more_specific_value_error_wins_over_the_generic_one():
    assert _one(report_failure(ClosureError("E_CLOSURE_KIND", detail="d")))["message"] == "d"
    bare = _one(report_failure(ClosureError("E_CLOSURE_KIND")))["message"]
    assert bare != "E_CLOSURE_KIND" and "E_CLOSURE_KIND" in bare and "no further detail" in bare


def test_a_stale_resource_version_gets_the_next_action():
    message = _one(report_failure(ClosureError("E_RESOURCE_VERSION_UNSUPPORTED", "/version", "theme x is old")))["message"]
    assert message == "theme x is old; see the current resource schema and migration notes before re-applying edits"


def test_aggregate_ingress_findings_gain_provenance_only_when_there_are_several():
    def finding(kind, identity, rule):
        return PresentationDiagnostic("E_RESOURCE_SCHEMA", kind, identity, "/p", rule, "m", "schema")

    single = report_failure(PresentationIngressRejected((finding("view", "v", "enum"),)))
    assert list(_one(single)) == ["code", "severity", "component", "sourceRef", "revisionRefs", "message"]
    assert _one(single)["code"] == "E_VIEW_SCHEMA"
    several = report_failure(PresentationIngressRejected((finding("view", "v", "enum"), finding("color-scheme", "c", None))))
    assert [item["code"] for item in several.diagnostics] == ["E_VIEW_SCHEMA", "E_COLOR_SCHEME_SCHEMA"]
    assert list(several.diagnostics[0])[-4:] == ["resourceKind", "resourceIdentity", "phase", "rule"]
    assert "rule" not in several.diagnostics[1]
    assert several.exit_code == 1


def test_render_outcomes_are_reported_like_the_cli_always_did():
    rejected = report_failure(RenderRejected([Diagnostic("E_CYCLE", "no", "/objects/a")], "core"))
    assert (rejected.status, rejected.exit_code) == ("rejected", 1)
    assert _one(rejected) == {"code": "E_CYCLE", "severity": "error", "component": "core", "sourceRef": "/objects/a",
                              "revisionRefs": [], "message": "no"}
    failed = report_failure(RenderFailed("E_R", "why", "layout", "/src"))
    assert (failed.status, _one(failed)["component"], _one(failed)["sourceRef"], failed.exit_code) == (
        "rejected", "layout", "/src", 1)


def test_core_diagnostics_are_reported_as_one_rejected_payload():
    report = rejection_report([Diagnostic("E_A", "a", "/a"), Diagnostic("E_B", "b", "/b")])
    assert [(item["code"], item["component"], item["sourceRef"]) for item in report.diagnostics] == [
        ("E_A", "core", "/a"), ("E_B", "core", "/b")]
    assert (report.status, report.exit_code) == ("rejected", 1)


def test_a_value_error_text_is_split_into_its_code_and_a_message_that_keeps_the_detail():
    row = _one(report_failure(ValueError("E_OPERATIONAL_SCHEMA: while parsing a flow node\ndid not find expected node")))
    assert row["code"] == "E_OPERATIONAL_SCHEMA"
    assert row["message"] == "E_OPERATIONAL_SCHEMA: while parsing a flow node\ndid not find expected node"
    assert _one(report_failure(ValueError("plain words")))["code"] == "E_PRESENTATION_REJECTED"


def test_an_exception_with_no_text_is_named_by_its_class():
    row = _one(report_failure(RuntimeError()))
    assert (row["code"], row["message"]) == ("E_TOOL_FAILURE", "RuntimeError")


def _row(code="E_A", source_ref="/a", message="m", **extra):
    return {"code": code, "severity": "error", "component": "core", "sourceRef": source_ref,
            "revisionRefs": [], "message": message, **extra}


def test_equal_rows_merge_into_the_first_with_a_count_and_a_single_row_is_untouched():
    single = _row()
    assert collapse_records([single]) == (single,) and "count" not in collapse_records([single])[0]
    merged = collapse_records([_row(), _row(), _row()])
    assert merged == (_row(count=3),)


def test_rows_that_differ_in_any_key_stay_apart_and_the_first_position_wins():
    rows = [_row("E_A", "/a"), _row("E_B", "/b"), _row("E_A", "/a"), _row("E_A", "/other"), _row("E_A", "/a", "other text"),
            _row("E_A", "/a", details={"k": 1}), _row("E_B", "/b")]
    merged = collapse_records(rows)
    assert [(item["code"], item["sourceRef"], item["message"], item.get("count")) for item in merged] == [
        ("E_A", "/a", "m", 2), ("E_B", "/b", "m", 2), ("E_A", "/other", "m", None),
        ("E_A", "/a", "other text", None), ("E_A", "/a", "m", None)]


def test_counts_add_when_already_merged_rows_are_merged_again():
    assert collapse_records([_row(count=2), _row(), _row(count=3)]) == (_row(count=6),)


def test_a_repeated_core_finding_is_one_row_with_a_count_in_the_rejection():
    report = rejection_report([Diagnostic("E_A", "a", "/a")] * 3 + [Diagnostic("E_B", "b", "/b")])
    assert [(item["code"], item.get("count")) for item in report.diagnostics] == [("E_A", 3), ("E_B", None)]

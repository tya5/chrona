"""TerseDiagnostic keeps its positional constructor and carries Core `details` through (#788 slice 0)."""
from chrona.core.diagnostics import Diagnostic
from chrona.terse.diagnostics import SourceRange, TerseDiagnostic

_RANGE = SourceRange(2, 3, 2, 9)


def test_a_terse_diagnostic_is_still_constructed_positionally():
    item = TerseDiagnostic("E_TERSE_X", "message", "/objects/a", _RANGE, "hint", "plan.chrona", "terse")
    assert (item.range, item.hint, item.source, item.component) == (_RANGE, "hint", "plan.chrona", "terse")
    assert item.details is None
    assert "details" not in item.as_dict()


def test_details_round_trip_through_with_source_and_as_dict():
    details = {"earliest": "2027-05-18", "from": {"object": "qa"}}
    item = TerseDiagnostic("E_FIXED_TARGET_VIOLATION", "m", "/relations/0", _RANGE, "h", None, "core", details=details)
    moved = item.with_source("plan.chrona")
    assert moved.details == details and moved.source == "plan.chrona"
    payload = moved.as_dict()
    assert payload["details"] == details and payload["source"] == "plan.chrona"
    assert list(payload)[:6] == ["code", "severity", "component", "sourceRef", "revisionRefs", "message"]
    assert list(payload).index("details") == 6


def test_a_terse_diagnostic_is_a_core_diagnostic_with_the_same_identity():
    assert TerseDiagnostic("E", "m", "/p", details={"k": 1}) == TerseDiagnostic("E", "m", "/p")
    assert isinstance(TerseDiagnostic("E", "m"), Diagnostic)

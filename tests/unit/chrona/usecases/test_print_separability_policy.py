"""Print claims enforce completed legend findings before adapter serialization."""
from copy import deepcopy

import pytest

from chrona.presentation.model.diagnostic_sources import (
    ColorPairFinding, DiagnosticProvenance, DiagnosticSubject,
)
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.usecases.render_review import RenderFailed, _enforce_print_claim


def _scheme(claim):
    return {"body": {"suitability": {"print": claim}}}


def _finding(vision="grayscale", delta=4.9999999):
    return DiagnosticProvenance(
        "W_LEGEND_COLOR_NOT_SEPARABLE",
        (DiagnosticSubject("legend-key:a", "A"), DiagnosticSubject("legend-key:b", "B")),
        ColorPairFinding(vision, delta))


@pytest.mark.parametrize("claim", ("print-friendly", "photocopy-friendly"))
def test_both_print_claims_enforce_the_same_raw_legend_finding(claim):
    with pytest.raises(RenderFailed) as captured:
        _enforce_print_claim(_scheme(claim), (_finding(),))
    error = captured.value
    assert error.code == "E_LEGEND_COLOR_NOT_SEPARABLE"
    assert error.source_ref == "/body/suitability/print"
    assert error.details == {
        "vision": "grayscale", "deltaE": 4.9999999, "minimumDeltaE": 5.0, "claim": claim,
        "sourceSubjects": [{"sourceRef": "legend-key:a", "title": "A"},
                           {"sourceRef": "legend-key:b", "title": "B"}],
    }


def test_unclaimed_print_finding_remains_nonblocking():
    _enforce_print_claim(_scheme("not-claimed"), (_finding(),))


@pytest.mark.parametrize("vision", ("normal", "protanopia", "deuteranopia", "tritanopia"))
def test_print_claim_does_not_enforce_other_vision_claims(vision):
    _enforce_print_claim(_scheme("print-friendly"), (_finding(vision),))


@pytest.mark.parametrize("claim", ("print-friendly", "photocopy-friendly"))
def test_real_completed_legend_warns_by_default_and_claim_precedes_svg(claim, monkeypatch, tmp_path):
    from tests.integration.test_realized_legends import ACTUAL, _detail, _parts, _render, _source

    parts = _parts()
    parts["theme"]["body"]["roles"]["actual"]["markCornerRadius"] = "mark-radius-square"
    scheme = parts["scheme"]["body"]
    # Distinct hues with nearly equal relative luminance, not a corpus palette.
    scheme["colors"]["accent"] = "#FF0000"
    scheme["colors"]["positive"] = "#009400"
    scheme["suitability"]["colorVision"] = ["none-claimed"]
    scheme["suitability"]["print"] = "not-claimed"
    detail = _detail()

    rendered = _render(tmp_path / "warning", _source(), actual=ACTUAL, parts=parts, detail=detail)
    warnings = [item.payload for item in rendered.warning_records
                if item.payload["code"] == "W_LEGEND_COLOR_NOT_SEPARABLE"
                and item.payload["vision"] == "grayscale"]
    assert warnings
    assert all(item["severity"] == "warning" for item in warnings)
    assert any({subject["title"] for subject in item["sourceSubjects"]}
               == {"Planned (planned)", "On track (actual)"} for item in warnings)
    assert rendered.artifact.content

    claimed = deepcopy(parts)
    claimed["scheme"]["body"]["suitability"]["print"] = claim
    adapter_calls = []

    def unexpected_adapter(_self, _surface):
        adapter_calls.append(True)
        raise AssertionError("claimed print failure must precede the SVG adapter")

    monkeypatch.setattr(V05SvgRenderer, "render", unexpected_adapter)
    with pytest.raises(RenderFailed) as captured:
        _render(tmp_path / "claimed", _source(), actual=ACTUAL, parts=claimed, detail=detail)
    assert captured.value.code == "E_LEGEND_COLOR_NOT_SEPARABLE"
    assert captured.value.source_ref == "/body/suitability/print"
    assert captured.value.details["vision"] == "grayscale"
    assert captured.value.details["claim"] == claim
    assert captured.value.details["deltaE"] < 5.0
    assert adapter_calls == []

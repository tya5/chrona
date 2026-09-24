import pytest

from tools.diagnostic_inventory import DiagnosticInventoryError, DiagnosticSite, discover, render, validate


def _site(*, anchor_line: int, layer: str = "user-facing-ingress", detail: bool = False) -> DiagnosticSite:
    return DiagnosticSite("E_SAMPLE", "src/chrona/usecases/sample.py", anchor_line, 4, "run", "ValueError", layer, detail)


def _default() -> dict:
    return {"code": "*", "disposition": "backlog", "nextAction": "add owner detail"}


def test_bare_ingress_requires_an_exact_code_classification():
    site = _site(anchor_line=10)

    validate((site,), (_default(),))

    validate((site,), ({"code": site.code, "disposition": "sufficient", "reason": "identifier is the complete message"}, _default()))


def test_policy_cannot_classify_detailed_or_internal_site():
    detailed = _site(anchor_line=10, detail=True)
    internal = _site(anchor_line=11, layer="internal")

    with pytest.raises(DiagnosticInventoryError, match="unknown=E_SAMPLE"):
        validate((detailed, internal), ({"code": detailed.code, "disposition": "sufficient", "reason": "stale"}, _default()))


def test_existing_allowlisted_code_does_not_hide_a_new_bare_site():
    first, second = _site(anchor_line=10), _site(anchor_line=11)

    policy = ({"code": "E_SAMPLE", "disposition": "backlog", "nextAction": "add detail"}, _default())
    validate((first, second), policy)

    report = render((first, second), policy)

    assert first.anchor in report
    assert second.anchor in report


def test_discovery_requires_a_complete_diagnostic_identifier(tmp_path):
    source = tmp_path / "src" / "chrona"
    source.mkdir(parents=True)
    (source / "sample.py").write_text(
        'value.startswith("E_")\nraise ValueError("E_COMPLETE")\n', encoding="utf-8"
    )

    sites = discover(tmp_path)

    assert [site.code for site in sites] == ["E_COMPLETE"]


def test_report_retains_detail_and_source_provenance():
    policy = ({"code": "E_SAMPLE", "disposition": "backlog", "nextAction": "add detail"}, _default())
    report = render((_site(anchor_line=10, detail=True), _site(anchor_line=11)), policy)

    assert "| `E_SAMPLE` | user-facing-ingress | yes |" in report
    assert "`src/chrona/usecases/sample.py:11:4`" in report

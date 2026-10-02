from pathlib import Path

import pytest

from tools.diagnostic_inventory import DiagnosticInventoryError, DiagnosticSite, discover, load_policy, render, validate


def _site(*, anchor_line: int, layer: str = "user-facing-ingress", detail: bool = False) -> DiagnosticSite:
    return DiagnosticSite("E_SAMPLE", "src/chrona/usecases/sample.py", anchor_line, 4, "run", "ValueError", layer, detail)


def _entry(sites: int = 1, disposition: str = "backlog") -> dict:
    entry = {"code": "E_SAMPLE", "disposition": disposition, "sites": sites}
    entry["reason" if disposition == "sufficient" else "nextAction"] = "why"
    return entry


def test_bare_ingress_requires_an_exact_code_classification():
    site = _site(anchor_line=10)

    validate((site,), (_entry(),))
    validate((site,), (_entry(disposition="sufficient"),))
    with pytest.raises(DiagnosticInventoryError, match="missing=E_SAMPLE"):
        validate((site,), ())


def test_policy_cannot_classify_detailed_or_internal_site():
    detailed = _site(anchor_line=10, detail=True)
    internal = _site(anchor_line=11, layer="internal")

    with pytest.raises(DiagnosticInventoryError, match="unknown=E_SAMPLE"):
        validate((detailed, internal), (_entry(),))


def test_a_new_bare_site_of_a_recorded_code_fails_the_ratchet():
    first, second = _site(anchor_line=10), _site(anchor_line=11)

    validate((first, second), (_entry(2),))
    with pytest.raises(DiagnosticInventoryError, match="grown=E_SAMPLE recorded=1 found=2"):
        validate((first, second), (_entry(1),))


def test_a_fixed_site_must_lower_the_recorded_count():
    with pytest.raises(DiagnosticInventoryError, match="lower=E_SAMPLE recorded=2 found=1"):
        validate((_site(anchor_line=10),), (_entry(2),))


def test_a_detailed_site_is_never_counted():
    validate((_site(anchor_line=10), _site(anchor_line=11, detail=True)), (_entry(1),))


def test_a_policy_entry_needs_a_positive_site_count(tmp_path):
    policy = tmp_path / "policy.yaml"
    template = ("version: chrona/resolvability-quality-policy/v0.1\ndiagnosticActionability:\n  bareDiagnostics:\n"
                "    - {code: E_SAMPLE, disposition: backlog, nextAction: x%s}\n")
    policy.write_text(template % ", sites: 3", encoding="utf-8")
    assert load_policy(policy)[0]["sites"] == 3
    for bad in ("", ", sites: 0", ", sites: true", ", sites: '3'"):
        policy.write_text(template % bad, encoding="utf-8")
        with pytest.raises(DiagnosticInventoryError, match="E_DIAGNOSTIC_POLICY_ENTRY"):
            load_policy(policy)


def test_the_real_tree_matches_the_recorded_baseline():
    """Ratchet gate (#829): no bare user-facing site outside the recorded counts; a fix lowers the policy."""
    root = Path(__file__).resolve().parents[3]
    validate(discover(root), load_policy(root / "conformance" / "resolvability-quality-policy-v0.1.yaml"))


def test_discovery_requires_a_complete_diagnostic_identifier(tmp_path):
    source = tmp_path / "src" / "chrona"
    source.mkdir(parents=True)
    (source / "sample.py").write_text(
        'value.startswith("E_")\nraise ValueError("E_COMPLETE")\n', encoding="utf-8"
    )

    sites = discover(tmp_path)

    assert [site.code for site in sites] == ["E_COMPLETE"]


def test_discovery_marks_transitively_imported_cli_module_as_user_facing(tmp_path):
    source = tmp_path / "src" / "chrona"
    (source / "app").mkdir(parents=True)
    (source / "presentation" / "model").mkdir(parents=True)
    (source / "app" / "cli.py").write_text(
        "import chrona.presentation.model.projection\n", encoding="utf-8"
    )
    (source / "presentation" / "model" / "projection.py").write_text(
        'raise ValueError("E_ACTUAL_REQUIRED")\n', encoding="utf-8"
    )

    sites = discover(tmp_path)

    assert [(site.code, site.layer) for site in sites] == [("E_ACTUAL_REQUIRED", "user-facing-ingress")]


def test_report_retains_detail_and_source_provenance():
    policy = (_entry(1),)
    report = render((_site(anchor_line=10, detail=True), _site(anchor_line=11)), policy)

    assert "| `E_SAMPLE` | user-facing-ingress | yes |" in report
    assert "`src/chrona/usecases/sample.py:11:4`" in report


def test_detail_inside_the_code_string_counts_as_detail(tmp_path):
    source = tmp_path / "src" / "chrona"
    source.mkdir(parents=True)
    (source / "sample.py").write_text(
        'raise ValueError("E_BARE")\n'
        'raise ValueError("E_BARE_COLON:")\n'
        'raise ValueError("E_LITERAL: the value")\n'
        'raise ValueError(f"E_FSTRING: {value}")\n'
        'raise ValueError(f"E_NO_DETAIL{value}")\n',
        encoding="utf-8",
    )

    detail = {site.code: site.has_detail for site in discover(tmp_path)}

    assert detail == {"E_BARE": False, "E_BARE_COLON": False, "E_LITERAL": True, "E_FSTRING": True}

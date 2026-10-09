from pathlib import Path

import pytest

from tools.diagnostic_inventory import DiagnosticInventoryError, DiagnosticSite, discover, load_policy, render, validate


def _site(*, anchor_line: int, layer: str = "user-facing-ingress", detail: bool = False) -> DiagnosticSite:
    return DiagnosticSite("E_SAMPLE", "src/chrona/usecases/sample.py", anchor_line, 4, "run", "ValueError", layer, detail)


def _entry(sites: int = 1, disposition: str = "backlog", *, code: str = "E_SAMPLE") -> dict:
    entry = {"code": code, "disposition": disposition, "sites": sites}
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


def test_diagnostic_identity_reads_are_not_construction_sites(tmp_path):
    source = tmp_path / "src" / "chrona"
    source.mkdir(parents=True)
    (source / "sample.py").write_text(
        'value.startswith("W_LAYOUT_LABEL_SUPPRESSED:")\n'
        'value.removeprefix("W_LAYOUT_LABEL_SUPPRESSED:")\n'
        'value.endswith("E_COMPLETE")\n'
        'value.removesuffix("E_COMPLETE")\n'
        'raise ValueError("E_COMPLETE")\n', encoding="utf-8")
    assert [site.code for site in discover(tmp_path)] == ["E_COMPLETE"]


def test_duplicate_helper_explicit_field_is_owner_detail(tmp_path):
    source = tmp_path / "src" / "chrona"
    source.mkdir(parents=True)
    (source / "sample.py").write_text(
        '_unique(values, "E_DETAIL_DUPLICATE_GROUP", field="/groupDetails/groupId")\n',
        encoding="utf-8")
    site, = discover(tmp_path)
    assert site.code == "E_DETAIL_DUPLICATE_GROUP" and site.has_detail


def test_typed_superclass_code_requires_unconditional_nonempty_detail(tmp_path):
    source = tmp_path / "src" / "chrona"
    source.mkdir(parents=True)
    (source / "sample.py").write_text(
        'class Detailed(ValueError):\n'
        ' def __init__(self, values):\n'
        '  super().__init__("E_DETAILED")\n'
        '  self.detail = f"count={len(values)}"\n'
        'class Empty(ValueError):\n'
        ' def __init__(self):\n'
        '  super().__init__("E_EMPTY")\n'
        '  self.detail = ""\n'
        'class Conditional(ValueError):\n'
        ' def __init__(self, value):\n'
        '  super().__init__("E_CONDITIONAL")\n'
        '  if value: self.detail = value\n', encoding="utf-8")
    assert {site.code: site.has_detail for site in discover(tmp_path)} == {
        "E_DETAILED": True, "E_EMPTY": False, "E_CONDITIONAL": False}


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


def _result_sources(root: Path, actual: str, snapshot: str = "") -> None:
    actual_path = root / "src" / "chrona" / "commands" / "actual_commands.py"
    actual_path.parent.mkdir(parents=True, exist_ok=True)
    actual_path.write_text(actual, encoding="utf-8")
    snapshot_path = root / "src" / "chrona" / "storage" / "snapshots.py"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(snapshot, encoding="utf-8")
    cli = root / "src" / "chrona" / "app" / "cli.py"
    cli.parent.mkdir(parents=True, exist_ok=True)
    cli.write_text(
        "from chrona.commands import actual_commands\n"
        "from chrona.storage import snapshots\n",
        encoding="utf-8",
    )


def test_result_diagnostic_tuples_cover_named_positional_and_keyword_arguments(tmp_path):
    _result_sources(
        tmp_path,
        """
def run(key, observation):
    ActualCommandResult('rejected', None, ('E_ACTUAL_BARE',))
    ActualIntakeCommandResult('rejected', None, (f'E_INTAKE_DETAIL: duplicate key {key!r}',), ())
    ActualIntakeCommandResult('rejected', None, (f'E_INTAKE_EMPTY: ',), ())
    ActualIntakeCommandResult(status='rejected', actual_set=None,
                              diagnostics=('E_INTAKE_KEYWORD',), dispositions=())
    ActualCommandResult('rejected', None, ('E_ACTUAL_OBSERVATION: missing observation',))
    unrelated(('E_UNRELATED_TUPLE',))
    ValueError(('E_UNRELATED_EXCEPTION_TUPLE',))
""",
        """
def capture(snapshot_id):
    SnapshotCaptureResult('rejected', None, diagnostics=(f'E_SNAPSHOT_DETAIL: {snapshot_id}',))
""",
    )

    sites = discover(tmp_path)
    result_sites = [site for site in sites if site.constructor in {
        "ActualCommandResult", "ActualIntakeCommandResult", "SnapshotCaptureResult",
    }]

    assert [(site.code, site.has_detail, site.layer) for site in result_sites] == [
        ("E_ACTUAL_BARE", False, "user-facing-ingress"),
        ("E_ACTUAL_OBSERVATION", True, "user-facing-ingress"),
        ("E_INTAKE_DETAIL", True, "user-facing-ingress"),
        ("E_INTAKE_EMPTY", False, "user-facing-ingress"),
        ("E_INTAKE_KEYWORD", False, "user-facing-ingress"),
        ("E_SNAPSHOT_DETAIL", True, "user-facing-ingress"),
    ]
    assert all("UNRELATED" not in site.code for site in sites)
    assert len([site for site in result_sites if site.code == "E_ACTUAL_BARE"]) == 1


def test_result_tuple_sites_participate_in_bare_detail_and_growth_ratchet(tmp_path):
    _result_sources(
        tmp_path,
        """
def run():
    ActualCommandResult('rejected', None, ('E_RESULT_SAMPLE', 'E_RESULT_SAMPLE'))
""",
    )
    sites = discover(tmp_path)
    policy = (_entry(code="E_RESULT_SAMPLE", sites=2),)

    validate(sites, policy)
    actual = tmp_path / "src" / "chrona" / "commands" / "actual_commands.py"
    actual.write_text(
        "def run():\n"
        "    ActualCommandResult('rejected', None, ('E_RESULT_SAMPLE: revision mismatch', 'E_RESULT_SAMPLE'))\n",
        encoding="utf-8",
    )
    detailed = discover(tmp_path)
    assert [site.code for site in detailed] == ["E_RESULT_SAMPLE", "E_RESULT_SAMPLE"]
    assert sorted(site.has_detail for site in detailed) == [False, True]
    with pytest.raises(DiagnosticInventoryError, match="lower=E_RESULT_SAMPLE recorded=2 found=1"):
        validate(detailed, policy)
    all_detailed = tuple(site for site in detailed if site.has_detail)
    with pytest.raises(DiagnosticInventoryError, match="unknown=E_RESULT_SAMPLE"):
        validate(all_detailed, policy)
    validate(all_detailed, ())

    actual.write_text(
        "def run():\n"
        "    ActualCommandResult('rejected', None, ('E_RESULT_SAMPLE', 'E_RESULT_SAMPLE'))\n",
        encoding="utf-8",
    )
    one_site_policy = (_entry(code="E_RESULT_SAMPLE", sites=1),)
    with pytest.raises(DiagnosticInventoryError, match="grown=E_RESULT_SAMPLE recorded=1 found=2"):
        validate(discover(tmp_path), one_site_policy)

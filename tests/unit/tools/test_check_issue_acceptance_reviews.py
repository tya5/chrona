from pathlib import Path

from tools.check_issue_acceptance_reviews import violations


def _write(root: Path, content: str) -> Path:
    reviews = root / "docs" / "reviews" / "current"
    reviews.mkdir(parents=True)
    (reviews / "review.md").write_text(content, encoding="utf-8")
    return reviews


def _local_evidence(reviews: Path) -> None:
    target = reviews / "tests" / "example.py"
    target.parent.mkdir()
    target.write_text("# evidence\n", encoding="utf-8")


def test_checker_accepts_each_issue_with_literal_rows_and_separate_programme_criteria(tmp_path):
    reviews = _write(tmp_path, """<!-- chrona:literal-acceptance/v1 -->
# Review

## Literal issue acceptance

### Issue #438

- Source: [Issue #438](https://github.com/tya5/chrona/issues/438)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | The literal requirement. | met | [test](tests/example.py) | — |

### Issue #450

- Source: [Issue #450](https://github.com/tya5/chrona/issues/450)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | The deferred requirement. | deferred | [test](tests/example.py) | [#451](https://github.com/tya5/chrona/issues/451) |

## Programme-level criteria (optional)

Additional evidence is separate.
""")
    _local_evidence(reviews)

    assert violations(reviews) == ()


def test_checker_rejects_missing_literal_row_and_invalid_disposition_or_successor(tmp_path):
    reviews = _write(tmp_path, """<!-- chrona:literal-acceptance/v1 -->
## Literal issue acceptance

### Issue #438

- Source: [Issue #438](https://github.com/tya5/chrona/issues/438)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | [Copied verbatim acceptance bullet] | partial | evidence | — |
| 2 | A moved requirement. | deferred | [test](tests/example.py) | — |

## Programme-level criteria (optional)
""")

    errors = violations(reviews)

    assert any(error.startswith("E_LITERAL_ACCEPTANCE_CRITERION:") for error in errors)
    assert any(error.startswith("E_LITERAL_ACCEPTANCE_DISPOSITION:") for error in errors)
    assert any(error.startswith("E_LITERAL_ACCEPTANCE_EVIDENCE:") for error in errors)
    assert any(error.startswith("E_LITERAL_ACCEPTANCE_SUCCESSOR:") for error in errors)


def test_checker_rejects_a_missing_local_evidence_link(tmp_path):
    reviews = _write(tmp_path, """<!-- chrona:literal-acceptance/v1 -->
## Literal issue acceptance

### Issue #438

- Source: [Issue #438](https://github.com/tya5/chrona/issues/438)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A literal requirement. | met | [missing](tests/missing.py) | — |

## Programme-level criteria (optional)
""")

    assert any(error.startswith("E_LITERAL_ACCEPTANCE_EVIDENCE:") for error in violations(reviews))


def test_checker_ignores_legacy_reviews_without_the_explicit_contract_marker(tmp_path):
    reviews = _write(tmp_path, "# Legacy review\n\nNo new contract.\n")

    assert violations(reviews) == ()

from pathlib import Path

import pytest

from tools.check_issue_acceptance_reviews import _cells, violations


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
    reviews = _write(tmp_path, r"""<!-- chrona:literal-acceptance/v1 -->
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


def test_checker_accepts_standard_escaped_pipe_in_literal_criterion(tmp_path):
    reviews = _write(tmp_path, r"""<!-- chrona:literal-acceptance/v1 -->
## Literal issue acceptance

### Issue #1560

- Source: [Issue #1560](https://github.com/tya5/chrona/issues/1560)
- Observed: 2026-10-16

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Accept technical-print \| muted-executive as alternatives. | met | [test](tests/example.py) | — |

## Programme-level criteria (optional)
""")
    _local_evidence(reviews)

    assert violations(reviews) == ()


@pytest.mark.parametrize(("line", "expected"), [
    (r"| left \| middle | right |", (r"left \| middle", "right")),
    (r"| left \\| right |", (r"left \\", "right")),
    (r"| left \\\| middle | right |", (r"left \\\| middle", "right")),
    (r"| left \\\\| right |", (r"left \\\\", "right")),
])
def test_cell_tokenizer_uses_backslash_parity_for_pipe_delimiters(line, expected):
    assert _cells(line) == expected


def test_escaped_pipe_does_not_weaken_the_five_cell_guard(tmp_path):
    reviews = _write(tmp_path, """<!-- chrona:literal-acceptance/v1 -->
## Literal issue acceptance

### Issue #1560

- Source: [Issue #1560](https://github.com/tya5/chrona/issues/1560)
- Observed: 2026-10-16

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | An actual extra column | met | [test](tests/example.py) | — | extra |

## Programme-level criteria (optional)
""")
    _local_evidence(reviews)

    errors = violations(reviews)
    assert any(error.startswith("E_LITERAL_ACCEPTANCE_ROW:") for error in errors)


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

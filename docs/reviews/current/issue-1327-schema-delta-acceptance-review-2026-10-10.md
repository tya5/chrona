<!-- chrona:literal-acceptance/v1 -->

# Issue 1327 acceptance

Source: [issue and current plan](https://github.com/tya5/chrona/issues/1327#issuecomment-6093224721).
Published baseline: `bcc0ecbb0aaf6e52001804b8d4f68259bee1743b`.
The offending composite allowance was already retired by PR #1320; no schema or ledger edits are added here.
The prune diagnostic preserves fail-closed proof and distinguishes pre-merge restatement from reviewed post-merge retirement.
Independent Luna review: passed; no layer, runtime behavior, or generated-output changes.

## Literal issue acceptance

### Issue #1327

- Source: [Issue #1327](https://github.com/tya5/chrona/issues/1327)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | `tools.schema_equivalence --base-rev origin/main` passes on main after the fix. | not met | [Local S0 result](https://github.com/tya5/chrona/issues/1327#issuecomment-6093245595): 38 equal schemas, 470 documents, 739 probes; L2+L3 35.9s against published `bcc0ecbb`. Exact published-main verification remains pending. | — |
| 2 | A schema PR rebased onto it, such as #1326, passes S0. | not met | Requires dev B's updated [PR #1326](https://github.com/tya5/chrona/pull/1326); no old-base CI is claimed as evidence. | — |

## Programme-level criteria (optional)

Focused command: `.venv/bin/python -m pytest -q tests/unit/tools/test_schema_expected_delta_lifecycle.py`
— 23 passed in 20.89s, including a real overlapping schema merge retaining the unproven record and actionable guidance.
S0 command: `.venv/bin/python -m tools.schema_equivalence --base-rev origin/main` — PASS.
Three-OS release CI and exact published-main evidence remain pending.

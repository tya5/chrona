<!-- chrona:literal-acceptance/v1 -->

# Issue 1327 acceptance

Source: [issue and current plan](https://github.com/tya5/chrona/issues/1327#issuecomment-6093224721).
Merged implementation: [PR #1330](https://github.com/tya5/chrona/pull/1330), source
`aee99e2a9ab0347ab27e050a352d4debdaec9b3c`; ready publication
`600f04b6a79ddd2a4761bc1c586ad0916409db74` also includes dev B's #1219.
The offending composite allowance was already retired by PR #1320; no schema or ledger edits are added here.
The prune diagnostic preserves fail-closed proof and distinguishes pre-merge restatement from reviewed post-merge retirement.
Independent Luna review: passed; no layer, runtime behavior, or generated-output changes.

## Literal issue acceptance

### Issue #1327

- Source: [Issue #1327](https://github.com/tya5/chrona/issues/1327)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | `tools.schema_equivalence --base-rev origin/main` passes on main after the fix. | met | [Post-merge main S0](https://github.com/tya5/chrona/issues/1327#issuecomment-6093224721): isolated checkout adopted published `aee99e2a`, exact tracked-tree identity confirmed against origin/main before execution; 38 equal schemas, 470 documents, 739 probes, L2+L3 34.9s. | — |
| 2 | A schema PR rebased onto it, such as #1326, passes S0. | met | [Independent dependent-PR S0 receipt](https://github.com/tya5/chrona/pull/1326#issuecomment-6093331466): public head `9cf57d63` adopts merged #1327; detached checkout's own venv passes full S0 against exact ready `600f04b6`, 37 equal/one View delta (five pointers), 470 documents/739 probes, L2+L3 36.8s. No edits or pruning. | — |

## Programme-level criteria (optional)

Focused command: `.venv/bin/python -m pytest -q tests/unit/tools/test_schema_expected_delta_lifecycle.py`
— 23 passed in 20.89s, including a real overlapping schema merge retaining the unproven record and actionable guidance.
S0 command: `.venv/bin/python -m tools.schema_equivalence --base-rev origin/main` — PASS.
Exact published-main and dependent-PR evidence are complete. Closure still requires
publication of this final table and successful three-OS release CI on its exact main.

<!-- chrona:literal-acceptance/v1 -->

# Issue #1306 — contributor test loop acceptance

Prepared implementation: `c9936062544f8b4ca0f3ed64015674deca10b6b4` on ready
main `4f4ee94ccc21c8d3c85021a1dc50a931d068e044`.
[Current design, architecture review and plan](https://github.com/tya5/chrona/issues/1306#issuecomment-6094278894).
Only contributor tooling/tests/CI change; product schemas and rendering stay unchanged.

## Literal issue acceptance

### Issue #1306

- Source: [Issue #1306](https://github.com/tya5/chrona/issues/1306)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A fresh venv set up exactly as CONTRIBUTING says passes `pytest tests/unit` (CI job that follows CONTRIBUTING literally). | not met | [Literal recipe runner and CI wiring tests](../../../tests/unit/tools/test_contributor_setup.py) pass; [Ubuntu release matrix](../../../.github/workflows/conformance.yml) executes the recipe and units in its new venv, then runs remaining tests without repeating units. Required containing-commit CI has not run. | — |
| 2 | A test or CI check that collecting any single test module does not call `declared_slides`/`reachable_view_paths` (or other corpus loaders) at import (checked by a collection hook or import-time spy). | met | [All-test source guard and fresh-process import spies](../../../tests/unit/tools/test_corpus_import_policy.py) pass, including alias/class/decorator/default/helper-chain regressions; all 342 collected case IDs in the four changed modules match the ready-base list exactly. | — |
| 3 | No unit test asserts wall-clock duration (checked by a grep-style test for budget assertions, with an allow-list for the benchmark job). | met | [Unit AST guard and deterministic-clock policy test](../../../tests/unit/tools/test_unit_timing_policy.py) pass (explicit empty benchmark allowlist); [semantic gate tests](../../../tests/unit/tools/test_schema_equivalence.py) use decode/validation/ingress counts. CLI/conformance retain their default runtime guard. | — |
| 4 | Do not edit `examples/**`. | met | [Prepared implementation diff](https://github.com/tya5/chrona/commit/c9936062544f8b4ca0f3ed64015674deca10b6b4) contains no authored examples, managed artifacts, product source or schemas. | — |

## Programme-level criteria (optional)

None. The issue remains open until row 1 and the required release gate are proven.

## Verification

Public geometry/properties/ledger, View schema and import policy: 264 passed,
45 skipped (47.22s). Setup/import/timing guards: 16 passed (8.62s).
Documented smoke loop plus setup tests: 42 passed (2.31s).
Schema-equivalence: 33 cases passed initially; an omitted two control-document
decode count was corrected, and the work-count case plus two policy tests passed
(3 cases, 40.78s). Expected-delta lifecycle: 23 passed (20.40s).
No local full-suite or completed CI claim. One eventual PR retains earlier
board publication priority; current-head snapshot and exact-main release remain required.

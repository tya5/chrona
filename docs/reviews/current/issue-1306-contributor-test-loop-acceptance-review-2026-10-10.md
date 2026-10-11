<!-- chrona:literal-acceptance/v1 -->

# Issue #1306 — contributor test loop acceptance

Implementation and collection-guard correction: `d12d10f2a92b34511e9717bd5da490bc003c24f8`, on
`wip/issue-1306-contributor-loop`, based on READY `fa862e40745aa134198dfe070aa347c451dd7ffe`.
[Current design, architecture review and plan](https://github.com/tya5/chrona/issues/1306#issuecomment-6094278894).
Only contributor tooling/tests/CI change; product schemas and rendering stay unchanged.

## Literal issue acceptance

### Issue #1306

- Source: [Issue #1306](https://github.com/tya5/chrona/issues/1306)
- Observed: 2026-10-12

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A fresh venv set up exactly as CONTRIBUTING says passes `pytest tests/unit` (CI job that follows CONTRIBUTING literally). | not met | [Literal recipe runner and CI wiring tests](../../../tests/unit/tools/test_contributor_setup.py) pass; [Ubuntu release matrix](../../../.github/workflows/conformance.yml) executes the recipe and units in its new venv, then runs remaining tests without repeating units. Required containing-commit CI has not run. | — |
| 2 | A test or CI check that collecting any single test module does not call `declared_slides`/`reachable_view_paths` (or other corpus loaders) at import (checked by a collection hook or import-time spy). | met | [All-test source guard and fresh-process import spy](../../../tests/unit/tools/test_corpus_import_policy.py) scan all 631 test modules, honoring only explicit pytest optional-dependency skips. Corpus helpers, example YAML reads/open and manifest discovery are forbidden during import. All 342 collected cases in the four original modules and 211 cases in the two corrected modules retain identical IDs against READY. | — |
| 3 | No unit test asserts wall-clock duration (checked by a grep-style test for budget assertions, with an allow-list for the benchmark job). | met | [Unit AST guard and deterministic-clock policy test](../../../tests/unit/tools/test_unit_timing_policy.py) pass (explicit empty benchmark allowlist); [semantic gate tests](../../../tests/unit/tools/test_schema_equivalence.py) use decode/validation/ingress counts. CLI/conformance retain their default runtime guard. | — |
| 4 | Do not edit `examples/**`. | met | [Prepared implementation diff](https://github.com/tya5/chrona/commit/c9936062544f8b4ca0f3ed64015674deca10b6b4) contains no authored examples, managed artifacts, product source or schemas. | — |

## Programme-level criteria (optional)

None. The issue remains open until row 1 and the required release gate are proven.

## Verification

Current READY focused setup/import/timing/loader-policy, agent-tools and
deadline batch: 232 passed (23.35 s). Final strengthened import guard and
documented quick smoke: 42 passed (5.11 s), including direct `Path.open` and
Python3.13 glob keyword forwarding. No existing assertion or corpus case was removed.
Independent detached checkout of `7dbe83d7`, with its own Python 3.13 venv
and only documented dev/render/CJK dependencies (MCP absent): documented quick
smoke plus contributor-setup, whole-import and unit-timing guards, 55 passed
(12.76 s); `pip check` reports no broken requirements and the editable import
points to that checkout. This is not evidence of a full unit-suite CI pass.
The all-module diagnostic found eager skill-launch data and deadline discovery
missed by the former four-module spy; session fixtures and collection hooks
now defer those reads without changing data, rendering or scheduler checks.
CI executes the documented fresh-venv recipe and unit suite once, then the
remainder; both suite failures and the finalizer remain authoritative.
This remains WIP evidence, not completed CI/release acceptance. Current-head
public artifacts and exact-main three-OS release are required before closure.

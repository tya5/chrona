<!-- chrona:literal-acceptance/v1 -->

# Issue #1306 — contributor test loop acceptance

Implementation and collection-guard correction: `d12d10f2a92b34511e9717bd5da490bc003c24f8`, on
`wip/issue-1306-contributor-loop`, based on READY `fa862e40745aa134198dfe070aa347c451dd7ffe`.
[Current design, architecture review and plan](https://github.com/tya5/chrona/issues/1306#issuecomment-6094278894).
Only contributor tooling/tests/CI change; product schemas and rendering stay unchanged.
CI launcher/selection guard correction: `ca2a69c22820b01e9ffc8b2c08ee6cc440b002a9`.
Portable import guard and deferred MCP fixtures: `4d1a5f9e`.

## Literal issue acceptance

### Issue #1306

- Source: [Issue #1306](https://github.com/tya5/chrona/issues/1306)
- Observed: 2026-10-12

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A fresh venv set up exactly as CONTRIBUTING says passes `pytest tests/unit` (CI job that follows CONTRIBUTING literally). | not met | [CI38163063134](https://github.com/tya5/chrona/actions/runs/38163063134/job/114539843361): literal recipe/conformance pass, fresh units7608 passed/1 failed/4 skipped; remaining2791 passed/46 skipped. The unit failure misreads Python `-m pytest` as pytest marker selection. Corrected guard passes locally; repaired-head CI remains required. | — |
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

CI failure disposition: `test_ci_corpus_selection::test_the_full_matrix_runs_every_test_including_corpus`
used a substring scan over the whole shell block. The correction inspects arguments
after each pytest entrypoint, bounded by shell command separators. Real marker,
keyword and deselect filters remain rejected; Python module launch is not a filter.
Executable/module launch, chained commands and negative filter spellings plus
setup/import/timing/quick-smoke guards:81 passed8.06s. No CI failure was bypassed,
no product rule changed, and the finalizer correctly rejected the failing unit suite.

All three OS jobs of CI38163063134 are terminal failures. macOS additionally
exposed an eager MCP launch-YAML read; Windows additionally hit the process
command-line limit while launching the whole-import spy. Both MCP modules now
read the same YAML in session fixtures, and the unchanged complete spy runs
through stdin instead of a long command argument. No module is excluded.
The MCP-floor job runs import/selection guards early, before stdio tests.
MCP2.0 plus setup/import/selection and MCP/CLI tests:93 passed53.13s;
after the stdin correction, setup/import/selection guards:44 passed4.67s.
CI38165240609 was cancelled before replaying known failures. A repaired-head
CI pass remains required; none of these focused results closes acceptance row1.

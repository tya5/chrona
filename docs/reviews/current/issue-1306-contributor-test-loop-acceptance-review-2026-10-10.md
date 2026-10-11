<!-- chrona:literal-acceptance/v1 -->

# Issue #1306 — contributor test loop acceptance

Verified source: `680a07216ee01a90808bb51f7d57c0b60c8bae1c`, on
`wip/issue-1306-contributor-loop`; integrated normally with the #1299/#1302
publication batch on trusted READY `b694b8589479bdf6bcf67ef9b1f3557067662f76`.
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
| 1 | A fresh venv set up exactly as CONTRIBUTING says passes `pytest tests/unit` (CI job that follows CONTRIBUTING literally). | met | [Exact-source CI38166148603, Ubuntu](https://github.com/tya5/chrona/actions/runs/38166148603/job/114549031547) creates the documented dev/render/CJK venv with no MCP SDK:7630 unit tests passed/4 optional skips; remainder2791 passed/46 skipped. Conformance, wheel smoke and failure-preserving finalizer pass. | — |
| 2 | A test or CI check that collecting any single test module does not call `declared_slides`/`reachable_view_paths` (or other corpus loaders) at import (checked by a collection hook or import-time spy). | met | [All-test source guard and fresh-process import spy](../../../tests/unit/tools/test_corpus_import_policy.py) scan all 631 test modules, honoring only explicit pytest optional-dependency skips. Corpus helpers, example YAML reads/open and manifest discovery are forbidden during import. All 342 collected cases in the four original modules and 211 cases in the two corrected modules retain identical IDs against READY. | — |
| 3 | No unit test asserts wall-clock duration (checked by a grep-style test for budget assertions, with an allow-list for the benchmark job). | met | [Unit AST guard and deterministic-clock policy test](../../../tests/unit/tools/test_unit_timing_policy.py) pass (explicit empty benchmark allowlist); [semantic gate tests](../../../tests/unit/tools/test_schema_equivalence.py) use decode/validation/ingress counts. CLI/conformance retain their default runtime guard. | — |
| 4 | Do not edit `examples/**`. | met | [Prepared implementation diff](https://github.com/tya5/chrona/commit/c9936062544f8b4ca0f3ed64015674deca10b6b4) contains no authored examples, managed artifacts, product source or schemas. | — |

## Programme-level criteria (optional)

None. Integration-head artifacts/checks and containing-review exact-main release
remain required; the source CI pass is not authority to close the issue.

## Verification

[Source CI38166148603](https://github.com/tya5/chrona/actions/runs/38166148603)
is terminal success on exact `680a0721`: all3 OS conformance/full pytest/wheel
smoke, MCP-floor and newest-Python reproduction. macOS10425 passed/46 skipped;
Windows10420 passed/51 skipped. Ubuntu's separate fresh units/remainder results
are linked in row1. No full local suite was duplicated.

Earlier CI38163063134 failures are resolved, not bypassed: the CI selection
guard parses pytest arguments rather than mistaking Python's `-m` for a marker;
both MCP modules defer unchanged launch YAML to session fixtures; the complete
import spy uses stdin rather than a Windows-overlong command argument. No module
exclusion or assertion removal. MCP2.0 focused batch93 passed53.13s; portable
guards44 passed4.67s. The dependency-only checkout at `8d57cb6a` has no MCP SDK,
correct editable import and clean requirements; quick smoke/guards81 passed6.95s.
Layout/Scene/adapters and domain semantics are untouched by this tooling slice.
Combined contributor/setup/import/timing/selection/schema-gate/MCP batch:
328 passed92.16s, including the new design-reuse and first-run test modules.

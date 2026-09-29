# Implementation Plan — Row-Following Draft Auto Sizing (#538)

Predecessors: [published design plan](issue-538-row-following-starter-work-record-2026-09-29.md), [design](../../design/issue-538-row-following-draft-auto-design-2026-09-29.md), and [architecture review](../reviews/issue-538-row-following-draft-auto-architecture-review-2026-09-29.md).
Successor: implementation/acceptance review after the slices below.

## Slice 1 — Publish normative sizing distinction

**Owners/files:** amend `docs/specification/33-intent-oriented-layout.md` §13.1.

State that Draft auto is content-sized independently of its finite synthetic closure seed; define least sufficient whole-profile allocation, positive empty-content floor, upward integral rounding, post-sizing fill, finite viewport minima, and fixed/capped fallback. Keep Specification 08 and 50 contracts aligned by reference. Review the amendment against #468 and its fixed-host correction before code. No schemas or preset resources are expected to change.

**Gate/publication:** publish the specification amendment as a coherent design unit before implementation; record its commit as the base for Slice 2.

## Slice 2 — Carry auto sizing intent into Layout

**Owners/files:** `src/chrona/presentation/model/closure.py`, `src/chrona/usecases/render_review.py`, `src/chrona/presentation/layout/engine.py`, and focused tests in `tests/unit/chrona/presentation/layout/test_intent_engine.py`. First close the [normal-flow measurement correction](../../design/issue-538-normal-flow-measurement-correction-2026-09-29.md) with shared track rules for column, row, grid, flow and overlay; do not substitute root `preferred_block` or a bounded probe heuristic.

Pass an explicit auto sizing floor/mode into Layout while retaining the 900-unit finite synthetic Context seed. Do not infer auto from a magic numeric block size. Make the resolver compute the least sufficient whole-profile extent from natural source requirements and profile chrome, round upward, and verify the complete final normal-flow LayoutManifest allocation. Grid natural measurement must match current single-span-derived row-track bases; multi-span shortage retains its existing fallback, without a new deficit distribution rule. Do not treat overflow bounds in the completed canvas as satisfying the selected viewport allocation. Preserve exact short-source evidence for fixed/capped hosts and the existing completed-canvas fallback. Explicit finite requests continue to use their requested minimum. Add cases for: compact requirement below 900; content above 900; finite 900 minimum; profile intrinsic minimum; empty requirement floor; deterministic rounding; missing source; multi-span overflow; and fixed/capped shortfall.

**Gate/publication:** focused Layout tests pass and the resolver result remains deterministic; publish this code/test slice before surface-level acceptance work.

## Slice 3 — Prove natural sizing and #504 fill composition

**Owners/files:** `src/chrona/presentation/layout/surface_composer.py` only if the existing pre-fill requirement path needs adjustment; `src/chrona/presentation/layout/presentation.py` only if a defect is found; tests in `tests/unit/chrona/presentation/layout/test_presentation.py` and relevant surface-composition tests.

Prove that row minima incorporate required marks/text/lanes, padding, and group headers before distribution. At the compact auto allocation, packed and filled profiles place rows at natural requirement absent surplus. An explicit larger finite minimum allows fill to consume only post-sizing surplus. A larger row count or requirement expands auto extent monotonically. Do not add another sizing pass based on fill-expanded rows.

**Gate/publication:** focused composition tests pass; inspect relevant serialized Layout/Scene evidence for natural row bounds and successor placement; publish the slice.

## Slice 4 — Starter and public materializer acceptance

**Owners/files:** extend `tests/integration/test_readable_defaults.py` and, if needed, `tests/integration/test_public_preset_evidence.py` or the relevant materializer conformance tooling. Inspect generated evidence from affected public materializers; do not edit preset sources absent a demonstrated need.

Initialize a fresh starter and render through the public CLI. Assert Scene viewport and completed timeline/table slots derive from the three starter rows and measured chrome rather than the 900-unit seed; inspect the actual SVG dimensions, rows, title/axis/legend/notes placement, and containment. Add row-count or high-requirement variants to prove growth. Retain a finite-viewport regression and a fixed/capped fallback regression. Run affected public materializers, batch-inspect Scene/SVG and any other generated formats, and compare intended bytes with baseline.

**Gate/publication:** focused tests and affected public materializers pass; record commands, commits, artifact byte diffs, actual output inspection, and any unrelated failures. Run the repository-required CI/release gate once the complete slice is ready; publish acceptance review with a row for every literal criterion. Keep #538 open if runtime evidence or a required CI gate is deferred.

## Expected change surface and non-changes

Likely production changes are confined to Draft ingress/request transport and the Layout content-allocation API/decision. Existing default View and Layout Profile declarations have no change. No schema migration, generated resource mirror, Theme, Scene schema, SVG adapter sizing policy, or immutable Context contract change is intended. Any newly discovered ownership or compatibility gap returns to a published design correction and amended plan before product code continues.

# Implementation Plan — Independent Axis Name Tables (#432)

**Published design base:** `80cd11ca67de536cbee7b107a2823e05ffeacc51`.
**Authorities:** [design](../../design/issue-432-axis-name-table-design-2026-09-26.md),
[architecture review](../../reviews/current/issue-432-axis-name-table-architecture-review-2026-09-26.md),
[specification](../../specification/63-axis-name-tables.md).
The [template-validation correction](../../design/issue-432-axis-name-table-template-validation-correction-2026-09-26.md)
and its [review](../../reviews/current/issue-432-axis-name-table-template-correction-review-2026-09-26.md)
are part of this plan's catalog acceptance gate.

## Literal issue acceptance gates

1. Under `ja-JP`, a month tier can render `Jan`, `January`, `1月` and `01`; under `en-US` it can render `1月`.
2. No two distinct month forms produce the same string under the same table without that being reported.
3. No axis label path branches on a language code.

## I432-1. Atomic contract, Layout and corpus migration

This is one publication unit because the View v0.22 ingress and immutable
Context pins cannot be separated from their public resources. Within the
unit, implement and run focused tests in this order:

1. **Catalog and equivalence.** Add a versioned wheel-owned table file under
   `src/chrona/resources/`, a typed validated loader in
   `src/chrona/presentation/model/` (and `src/chrona/resources/__init__.py`
   accessor if needed), a finite resource schema under `schemas/`, a checked
   `docs/diagnostics/axis-name-tables.md` audit with a tool under `tools/`,
   and schema/diagnostic inventory updates. Tests cover twelve-month arrays,
   all closed forms/placeholders, duplicate coverage, false declarations,
   invalid IDs and package/wheel availability.
2. **View and Layout.** Add `schemas/view-v0.22.schema.yaml`; transition
   v0.21 in schema inventory, switch `presentation/contracts/resources.py`
   runtime ingress, and add `label.nameTable` in every labels-tier branch.
   Normalize a selected ID in `presentation/review/v05_content.py` into
   `AxisLabelIntent` (`presentation/model/surface_content.py`). Replace
   language branching in `presentation/layout/axis.py` with selected-table
   formatting. `surface_composer.py` must use the same selected table for
   automatic trial and final placement, record it on `AxisTierOutcome` in
   `surface_quality.py`, and emit the noncanonical-equivalence diagnostic.
   Remove the now-unused Layout request locale rather than retaining an
   unused environment field. Update every constructor/caller and structural
   delivery check affected by these typed fields.
3. **Resources and evidence.** Migrate all source Views in `examples/`,
   relevant `tests/fixtures/`, wheel-mirrored examples, derived/preset source
   identities and immutable Context pins to v0.22. Change only intended axis
   text and metadata, preserving temporal intervals, mark geometry and
   unrelated paint. Regenerate all affected public Scene/SVG pairs, diagnostic
   inventory, example/declared-value inventories and other checked evidence
   via repository tools. Audit every generated Scene/SVG diff in one batch;
   raster-check the Japanese Controller Z slide and representative English
   slides if any visible text changes.

**Focused tests:** `tests/unit/chrona/presentation/layout/test_presentation_axis.py`,
`test_axis_placement.py`, `test_surface_quality.py`, View schema/closure
integration tests, `test_v05_builder.py`, catalog/audit tests, public CLI
materializer byte test, and a structural test rejecting a language-code
branch in the axis formatter path. Add a real View/Context integration case
for all five literal cross-language outputs and an automatic-tier case proving
candidate-fit/final-text identity. Add negative schema cases for non-label
use, invalid table IDs and stale v0.21 runtime input.

**Acceptance before push:** all focused tests and
`python conformance/run_conformance.py` pass; public materializers reproduce
byte-for-byte; schema inventory and package resource checks pass; generated
diffs have no unintended geometry/paint changes; every literal criterion has
direct evidence. Fetch `origin/main`, check ahead/behind and staged targets,
then publish this whole slice. Do not publish a red intermediate contract.

## I432-2. Release and acceptance review

Inspect the material implementation's GitHub CI: three-OS full pytest and
conformance, wheel/smoke, and newest-Python public-materializer reproduction.
If red, identify every failing check, distinguish introduced from independent
failures and correct before acceptance. Do not repeat a costly local full
pytest without a concrete CI-specific risk.

Write `docs/reviews/current/issue-432-axis-name-table-acceptance-review-2026-09-26.md`
using the literal-acceptance marker and a row for each exact criterion. Record
the implementation commit, commands, artifact diff and raster review, CI run,
architecture findings and any migration impact. Publish the review as a
separate coherent commit, verify remote and CI state, then close #432 only if
every literal row is met. Leave reviewer-maintained #454 and pending #462
unchanged.

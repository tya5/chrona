# Issue #402 — Table Fact Realization Acceptance Review

**Status:** accepted.
**Implementation:** `a362989f`, `f9419634`
**CI:** [run 36119894231](https://github.com/tya5/chrona/actions/runs/36119894231)

## Accepted boundary

The release gives table facts their own declared semantic identities and
preserves them through normalized review content, completed Layout text
placements, and Scene projection.  It does not reuse plot-label identities:
the table-cell metadata invariant requires the `table-cell` purpose, while
plot labels retain their distinct `finish-delta` purpose.

| Requirement | Evidence | Result |
| --- | --- | --- |
| Finish-delta table facts select declared variance roles | `tableVarianceAhead`, `tableVarianceOnTrack`, and `tableVarianceBehind` are selected from normalized comparison facts and registered as `table-cell` identities. | Pass |
| Missing actual observations are distinguishable | `missingActualCell` is selected only for an unobserved `missingActual` fact; observed values and unrelated cells remain neutral `tableCell`. | Pass |
| Layout owns the semantic placement closure | typed `TableCellContent` is normalized before Layout, and `TextPlacement.semantic_id` carries the selected identity. | Pass |
| Scene remains a projection | Scene resolves the identity supplied by completed table content and emits primitives; it does not infer fact state or choose a table role. | Pass |
| Public evidence reflects the admitted state families | HALCYON corpus fixtures and regenerated inspection Scenes make both table families realized in `semantic-realization-coverage.md`. | Pass |

## Verification

* focused normalization, Layout, Scene, reachability, and realization-report
  tests passed (including the 57-test presentation focus);
* `pytest --lf -x`: 6 passed;
* public HALCYON and Orion materialization, all-corpus regeneration,
  `python conformance/run_conformance.py`, and generated-artifact review
  passed;
* CI run 36119894231 passed on Ubuntu, macOS, and Windows, including
  conformance, structural checks, checked documentation/report generation,
  parallel pytest, wheel build, and installed-wheel smoke.

## Architecture review

State selection is confined to review-content normalization.  Layout composes
the resulting typed placement, and Scene only projects it through the semantic
registry.  This maintains the Project/View -> Layout -> Scene -> adapter
authority chain, leaves routing and text geometry outside Scene, and keeps the
pre-existing plot-label semantics independent of table rendering.

## Follow-up disposition

Issue #402 is complete.  Issue #414 remains open because its separate
annotation-purpose realization depends on #413.

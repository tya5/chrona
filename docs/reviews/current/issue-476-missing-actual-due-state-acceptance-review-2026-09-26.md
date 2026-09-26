<!-- chrona:literal-acceptance/v1 -->

# Acceptance Review — Due-State Missing Actual (#476)

**Authority:** [design](../../design/issue-476-missing-actual-due-state-design-2026-09-26.md), [architecture review](issue-476-missing-actual-due-state-architecture-review-2026-09-26.md), [implementation plan](../../planning/active/issue-476-missing-actual-due-state-implementation-plan-2026-09-26.md). **Public implementation:** `8153f7296daecd94f71a6a66aee10f2017e1ada2`; generated diagnostic/contrast evidence correction: `44b5604e16bd7fa2c1c3e4728a577fcbb4e200d0`.

## Verification on published main

View now derives one typed `ObservationState` from selected Actual observation
presence, explicit `asOf`, and the canonical planned due endpoint. Semantic
roles, table cells, summary counts and Layout marks consume the same state.
Layout alone completes mark geometry; Scene and SVG serialize it. No Project,
Actual, View, Theme, schema or adapter contract was changed. The migration is
intentional: future unobserved items lose a misleading missing mark and the
table `missingActual` cell uses its declared missing placeholder instead of
claiming “Recorded.”

- Focused tests: `python -m pytest -q tests/unit/chrona/presentation tests/integration/test_render.py` — **529 passed**. Tests cover span/point due equality, future, recorded-incomplete, no-as-of, explicit/shared/snapshot/scenario projection, table tri-state, summary availability, Layout/Scene projection, and HALCYON Scene/SVG.
- `python tools/regenerate_public_examples.py --write --jobs 4`, followed by `--check --jobs 4` — **21 public slides regenerated and byte-reproduced**. Eighteen Scene/SVG pairs changed; the other three remain byte-identical. All removed primitive IDs in the changed Scenes are `missing-actual:*`; no primitive IDs were added. Diagnostics arrays did not change. A few dependency routes changed deterministically because the removed marks cease to be obstacles.
- All 18 changed SVGs were rasterized in one batch. HALCYON programme board and mission brief, Controller Z executive, and Orion gates were visually inspected as representative layouts; no unexpected blank row, mark removal, crop, or text disappearance was observed.
- `python tools/presentation_contrast.py --check` and `python tools/diagnostic_inventory.py --check` pass after regenerating the derived reports. The contrast report's `missingActual` primitive count falls from 93 to 15, and `missing-actual-cell` from 21 to 3, with zero contrast errors. The diagnostic inventory changes are source-location shifts, not new diagnostic codes.
- [CI run 36236959373](https://github.com/tya5/chrona/actions/runs/36236959373) on `44b5604e`: all four jobs green. Full pytest: Ubuntu **1084 passed, 23 skipped**; Windows **1084 passed, 23 skipped**; macOS **1088 passed, 19 skipped**. The three-OS conformance and wheel/smoke gates and newest-Python public-materializer reproduction passed. Prior run 36236818787 was red only because the two derived reports above were stale; Ubuntu/macOS pytest passed there as well, and its Windows job was canceled by the corrective push.

## Literal issue acceptance

### Issue #476

- Source: [Issue #476](https://github.com/tya5/chrona/issues/476)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Direct evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | On HALCYON-1 at as-of 2027-08-20, items planned to finish after 2027-08-20 carry no missing-actual mark. | met | `test_halcyon_missing_actual_is_due_only_and_tvac_boundary_is_inclusive`; public `02-programme-board.scene.json` removes all nine named future marks while retaining due `pdr` and `launch-contract`; SVG raster review. | — |
| 2 | Items due on or before as-of with no observation still carry it. `tvac` (planned finish 08-20, no observation) is the boundary case, and a test covers it. | deferred | Inclusive span/point unit tests and a test-only HALCYON Actual copy with only `tvac-in-progress` removed prove the due-day mark in Scene and SVG. The **published** `examples/halcyon-1/actual.yaml` has `tvac-in-progress`, so shipped TVAC correctly remains `recorded` with `W_LAYOUT_ACTUAL_INCOMPLETE:tvac` and no missing mark. The literal parenthetical remains factually false for shipped HALCYON. | [Owner clarification request](https://github.com/tya5/chrona/issues/476#issuecomment-5845498008) and [fixture-plan amendment](../../planning/active/issue-476-missing-actual-due-state-design-plan-amendment-2026-09-26.md). |
| 3 | The `missingActual` table cell follows the same rule. | met | HALCYON `01-mission-brief.scene.json` shows future rows as `—`, shipped observed TVAC as `Recorded`, and the test-only no-TVAC boundary as `Missing`; `test_missing_actual_table_fact_follows_observation_state` covers all four states. | — |

## Architecture and release disposition

The observation fact is derived once in View and consumed without date
recalculation in Layout, table and summary. Scene performs no due-state policy
or placement repair; SVG/PNG adapters remain serializers. Recorded incomplete
Actual is not misrepresented as missing. The generated-scene, visual,
contrast and CI evidence support the implementation. **Leave #476 open** until
the issue owner amends or confirms the contradictory TVAC wording and the
deferred literal row can be accepted; do not reinterpret the shipped corpus to
make a checkbox green.

# L1 Project and Current Presentation Evidence Review (#467, #494)

**Status:** L1 Project identity/data migration and dependent current presentation evidence are published; all lane and route acceptance remains deferred. **Base:** `origin/main` `c951d4f9b820c2eb241b5974ad023f0bce511ecd`. **L1 result:** `63f86e6a033d22cca5e9d2102ebed7ef958f3321`. **Evidence refresh:** `c951d4f9b820c2eb241b5974ad023f0bce511ecd`. **Plan:** [L1 current-Project revision implementation amendment](../../planning/active/issue-467-494-l1-current-project-revision-implementation-plan-amendment-2026-09-27.md) and [L0/L3 gate amendment](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md). **Scheduler evidence:** [L0 current-main feasibility record](../../research/presentation/issue-467-494-l0-current-main-feasibility-2026-09-27.md).

This review records the published L1 data and presentation changes. It does not accept either issue: the published mainline has no lane-mode implementation, so none of the lane membership, name-placement, or route criteria can yet be demonstrated. The issues remain open.

## Published L1 evidence

Commit `63f86e6a033d22cca5e9d2102ebed7ef958f3321` changes the current Project's `avionics-bustest` lag from 2wd to 4wd, updates all 15 Context Project pins, and refreshes the dependent current materializer outputs: 15 Contexts, 15 Scene JSON files, and 9 SVG files were changed/generated in the evidence batch. The repository also has SVGs outside that refreshed set; this count describes the L1 batch, not the entire SVG inventory.

The ordinary scheduler measurement records bus-test planned dates as Apr 29–May 13 at 2wd and May 3–May 17 at 4wd (2027). The 4wd choice aligns the named planned chain's bus-test start after avionics actual finish on Apr 30; it does not change Actual or the frozen baseline. The Project relation now declares `lag: 4wd` in [`project.yaml`](../../../examples/halcyon-1/project.yaml), and the materialized board is [`02-programme-board.svg`](../../../examples/halcyon-1/generated/02-programme-board.svg). This is schedule evidence only and establishes no lane assignment.

The scheduled CDR member label on `01-mission-brief` is now suppressed by the existing containment policy and reported once as `W_LAYOUT_LABEL_SUPPRESSED:member-label:cdr:cdr`, with `I_LAYOUT_PLOT_LABELS_SUPPRESSED:surface=table-timeline;count=1`. The L1 commits did not change that policy. The focused regression assertion is in [`test_render.py`](../../../tests/integration/test_render.py). The refreshed public presentation reports are [`presentation-contrast.md`](../../diagnostics/presentation-contrast.md) and [`presentation-font-identity.md`](../../diagnostics/presentation-font-identity.md), updated at `c951d4f9` to match the new schedule and presentation evidence.

The first L1 [CI run 36298186716](https://github.com/tya5/chrona/actions/runs/36298186716) found two stale presentation reports and a render test whose absence-of-suppression assumption became false after the scheduled date change. `c951d4f9` refreshed the reports and asserted the resulting CDR suppression and exact count; it did not alter the Layout policy. The replacement [CI run 36298528541](https://github.com/tya5/chrona/actions/runs/36298528541) passed Ubuntu, macOS, and Windows conformance/full pytest/wheel smoke, plus newest-Python public-materializer reproduction. The 28-slide public materializer batch passed locally after the correction.

## Literal issue acceptance

### Issue #467

- Source: [Issue #467](https://github.com/tya5/chrona/issues/467)
- Observed: 2026-09-27

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A lane row mode exists. On `02-programme-board` the 26 items occupy at most 12 lanes, with the chain `structure → avionics → bus-test` on one lane. | deferred | Current-main L0 record documents that the checked-in View schema/composer has no lane mode and cannot measure membership; L1's 4wd scheduler result is not lane geometry. | [L3 lane and route implementation gate](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md) |
| 2 | Every packed task and milestone has a visible name on the slide; no `W_LAYOUT_LABEL_SUPPRESSED` for a packed item on any committed slide. | deferred | No packed slides exist on the reviewed mainline; public SVG/Scene outputs reflect the current automatic layout, not lane labels. | [L3 lane and route implementation gate](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md) |
| 3 | Lane assignment is deterministic, and a test shows that one inserted item does not reorder unrelated lanes. | deferred | There is no published lane allocator or insertion-stability test on this base. | [L3 lane and route implementation gate](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md) |
| 4 | Deltas remain visible for packed items that have them. | deferred | Current refreshed outputs do not exercise packed-item delta placement; lane-mode visibility remains unmeasured. | [L3 lane and route implementation gate](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md) |
| 5 | New Views and the packaged presets default to lanes; `automatic` still renders exactly as today. | deferred | No lane default is published. L1 refreshes existing current-Project outputs and does not change View defaults or packaged presets. | [L3 lane and route implementation gate](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md) |
| 6 | At least three committed slides use lanes (for example `01`, `02` and `06`), and their evidence is reproducible. | deferred | The 15 Scenes and 9 SVGs at the reviewed base are current materializer evidence, not three lane-mode slides. | [L3 lane and route implementation gate](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md) |

### Issue #494

- Source: [Issue #494](https://github.com/tya5/chrona/issues/494)
- Observed: 2026-09-27

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | On `02-programme-board` (lanes), no relation is suppressed for `egress-collision`, and every remaining suppression is listed with a measured cause. | deferred | The reviewed public Scene is automatic mode. The current-main L0 record explains that route cause and lane egress cannot be measured before the L3 engine/instrumentation exists. | [L3 lane and route implementation gate](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md) |
| 2 | `test_lane_relation_routes_never_cross_a_required_lane_label` still passes on 02, 11 and 12: no route crosses any lane or member label. | deferred | The named lane-route test and lane labels are not present in this published mainline evidence. | [L3 lane and route implementation gate](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md) |
| 3 | Lane count and lane membership on 02 are unchanged, or any change is attributed. | deferred | No accepted lane count or membership exists in the current published Scene against which to compare. | [L3 lane and route implementation gate](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md) |

## Architecture conclusion

L1 changes Project scheduling data, Context identity pins, materialized evidence, and current diagnostics. It does not implement lane geometry or route placement. Responsibility remains with the existing scheduler for date computation, materializer for Context-pinned resource closure, Layout for any future completed lane geometry and routes, Scene for carrying those completed primitives/relations, and SVG adapters for serialization. The evidence refresh also confirms the existing Layout suppression policy's result for the CDR label; the policy itself is unchanged.

All nine literal acceptance rows are `deferred`; neither issue is ready to close. The L1 release gate is green at run `36298528541`. Continue with the approved L2/L3 lane contract and implementation sequence in the linked active plan.

# Implementation and Acceptance Review — View v0.27 Lane Contract (#467, #494)

**Status:** L2 contract implementation reviewed; all nine lane and route acceptance criteria remain deferred. **Commit:** `ba8d99d0` (`feat: stage View v0.27 lane contract without enabling lanes`). **Accepted L1 base:** `c4a03d04` ([L1 project and current presentation evidence review](issue-467-494-l1-project-evidence-acceptance-review-2026-09-27.md)). **Design:** [v0.27 contract clarification](../../design/issue-467-view-v027-contract-clarification-2026-09-27.md) and [phase/version correction](../../design/issue-467-lane-rows-phase-and-version-correction-2026-09-27.md). **Architecture review:** [v0.27 contract review](issue-467-view-v027-contract-architecture-review-2026-09-27.md). **Implementation plan:** [L2 implementation amendment](../../planning/active/issue-467-view-v027-contract-implementation-amendment-2026-09-27.md).

## L2 implementation and evidence

L2 adds the View v0.27 schema and schema inventory registration, marks v0.26 as transitioning, normalizes the finite lane fields into typed contracts, and migrates 34 versioned View declarations. It does not enable lanes in any corpus View or preset and does not implement lane geometry or route placement. Unsupported lane rendering fails closed until the L3 engine exists. `laneTable` is admitted only for lane mode; lane mode rejects `tableColumns`, while explicit collision allocation remains explicit-only. Lane labels require `title` and `visible-overflow`.

The focused contract and migration suite passed: **90 passed**. The full public-materializer batch passed: **28 passed**. All 28 public Scene digests changed because their View content identity records the migrated version declarations; all 28 generated SVGs remained byte-identical. The regenerated Scene/SVG pairs were inspected as a batch. These are materializer and contract results, not rendered lane acceptance evidence.

The required [CI release gate 36298827030](https://github.com/tya5/chrona/actions/runs/36298827030) passed all Ubuntu, macOS and Windows conformance/full pytest/wheel-smoke jobs and the newest-Python public-materializer reproduction job on `ba8d99d0`.

<!-- chrona:literal-acceptance/v1 -->

## Literal issue acceptance

### Issue #467

- Source: [Issue #467](https://github.com/tya5/chrona/issues/467)
- Observed: 2026-09-27

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A lane row mode exists. On `02-programme-board` the 26 items occupy at most 12 lanes, with the chain `structure → avionics → bus-test` on one lane. | deferred | [The fail-closed guard](../../../src/chrona/usecases/render_review.py) prevents public lane rendering; the schema alone supplies no membership count. | [L0/L3 implementation gate](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md) |
| 2 | Every packed task and milestone has a visible name on the slide; no `W_LAYOUT_LABEL_SUPPRESSED` for a packed item on any committed slide. | deferred | [The fail-closed guard](../../../src/chrona/usecases/render_review.py) prevents packed output, so no visible-name evidence exists yet. | [L0/L3 implementation gate](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md) |
| 3 | Lane assignment is deterministic, and a test shows that one inserted item does not reorder unrelated lanes. | deferred | [The L2 implementation plan](../../planning/active/issue-467-view-v027-contract-implementation-amendment-2026-09-27.md) excludes the allocator; insertion stability requires L3 tests. | [L0/L3 implementation gate](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md) |
| 4 | Deltas remain visible for packed items that have them. | deferred | [The v0.27 schema](../../../schemas/view-v0.27.schema.yaml) admits label content but no packed delta is rendered; source-view delta migration remains an L3 evidence gate. | [L0/L3 implementation gate](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md) |
| 5 | New Views and the packaged presets default to lanes; `automatic` still renders exactly as today. | deferred | [The packaged preset Views](../../../src/chrona/resources/presets/bundles/editorial-readable-default/view.yaml) remain automatic; the 28 unchanged SVGs prove only that L2 did not alter current rendering. | [L0/L3 implementation gate](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md) |
| 6 | At least three committed slides use lanes (for example `01`, `02` and `06`), and their evidence is reproducible. | deferred | [The board View](../../../examples/halcyon-1/views/02-programme-board.yaml) remains automatic; the 28-slide materializer batch reproduces only current non-lane output. | [L0/L3 implementation gate](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md) |

### Issue #494

- Source: [Issue #494](https://github.com/tya5/chrona/issues/494)
- Observed: 2026-09-27

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | On `02-programme-board` (lanes), no relation is suppressed for `egress-collision`, and every remaining suppression is listed with a measured cause. | deferred | [The fail-closed guard](../../../src/chrona/usecases/render_review.py) supplies no lane route or cause-specific measurement. | [L0/L3 implementation gate](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md) |
| 2 | `test_lane_relation_routes_never_cross_a_required_lane_label` still passes on 02, 11 and 12: no route crosses any lane or member label. | deferred | [The L2 implementation plan](../../planning/active/issue-467-view-v027-contract-implementation-amendment-2026-09-27.md) excludes lane geometry; the required three-slide crossing test belongs to L3. | [L0/L3 implementation gate](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md) |
| 3 | Lane count and lane membership on 02 are unchanged, or any change is attributed. | deferred | [The board View](../../../examples/halcyon-1/views/02-programme-board.yaml) remains automatic, so no accepted lane count or membership exists in L2 output. | [L0/L3 implementation gate](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md) |

## Programme-level criteria (optional)

None. The nine literal issue criteria above remain the release gates.

## Architecture and release disposition

The change stays within the View resource contract, schema registry, and typed normalization boundary. Layout remains responsible for future completed lane geometry, required label placement and relation routes; Scene carries completed primitives and paint relations; adapters serialize them. L2 adds no parallel layout behavior and preserves current `automatic` and `explicit` rendering. Scene digest changes are attributable to the View content identity migration; the SVG byte comparison confirms no L2-only rendered changes.

All nine literal criteria are deferred, so #467 and #494 remain open. The L2 release gate is green at `ba8d99d0`; the next public base for L3 is this reviewed commit and its CI evidence. Lane geometry, routes and default activation remain separate L3 work.

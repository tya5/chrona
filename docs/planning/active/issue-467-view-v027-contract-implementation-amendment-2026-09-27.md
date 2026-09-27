# Implementation Amendment — View v0.27 Lane Contract (#467)

**Amends:** [scheduler-only L0 and L3 gate plan](issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md). **Design:** [v0.27 contract clarification](../../design/issue-467-view-v027-contract-clarification-2026-09-27.md). **Review:** [architecture review](../../reviews/current/issue-467-view-v027-contract-architecture-review-2026-09-27.md).

## L2 scope and acceptance

L2 copies the then-live View schema to v0.27, registers it as live and v0.26 as transitioning, normalizes the finite lane fields into typed contracts, and migrates tracked View declarations without selecting lane mode in corpus Views or presets.

The v0.27 schema requires `rows.laneTable` only for `rows.mode: lanes`; it rejects that property in `automatic` and `explicit`. Lane mode rejects `tableColumns` because the current grammar's columns are item-subject declarations; lane summaries use only the separate group/lane `laneTable`. Explicit `trackAllocation: collision` remains explicit-only. Lane labels require `title` and `visible-overflow`; a source View's visible delta-column promise must migrate to `finishDelta` label content and be proven in L3 acceptance evidence. The latter is a migration gate, not a universal schema constraint.

Focused checks must cover accepted lane declarations, invalid combinations (including `laneTable` on automatic and explicit rows), explicit collision opt-in, typed normalization, and fail-closed rendering before the L3 engine. Validate all migrated Views, packaged preset resources and schema inventory. No lane-default or preset migration is part of L2.

## Publication evidence after L1

Rebase on the accepted L1 base before materialization. Run the full public materializer check/write batch and inspect every declared Scene/SVG pair. The 28 public Scene files record View content identity and therefore require regeneration after these version-line changes. Check all 28 SVG outputs; L2 alone is expected to leave their rendered bytes unchanged, while any L1 schedule effects are evaluated from the accepted L1 artifacts. Run packaged preset, bundled-default/starter and wheel-resource checks for the eight updated package View resources.

L2 is independently publishable only with the updated resource declarations, schema inventory and any required generated Scene evidence together. It claims no #467/#494 lane acceptance; L3 remains the first lane-engine and route-evidence slice.

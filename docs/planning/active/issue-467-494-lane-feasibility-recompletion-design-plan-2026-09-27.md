# Design Plan — Recomplete Lane Feasibility and Route Evidence (#467, #494)

**Issues:** [#467](https://github.com/tya5/chrona/issues/467) and [#494](https://github.com/tya5/chrona/issues/494). **Published baseline:** `33a1ddc0ff750da2ad2a3d0b274658914614af2c` on `main` (the #489 acceptance review; its CI must finish before the next publication). **Predecessors:** the [original design plan](issue-467-lane-packing-design-plan-2026-09-26.md), [selected design](../../design/issue-467-collision-aware-lane-rows-design-2026-09-26.md), [phase/version correction](../../design/issue-467-lane-rows-phase-and-version-correction-2026-09-27.md), [ladder correction](../../design/issue-467-lane-rows-l0-ladder-correction-2026-09-27.md), [architecture re-review](../../reviews/current/issue-467-lane-rows-phase-correction-architecture-review-2026-09-27.md), [L0 record](../../research/presentation/issue-467-lane-rows-l0-feasibility-2026-09-27.md), and [implementation amendment](issue-467-lane-rows-implementation-amendment-2026-09-27.md). This plan does not accept or merge the remote WIP lane branch.

## Published facts, leads, and unverified claims

- `main` has the corrected #466 Layout phase contract and View v0.26, but no accepted `rows.mode: lanes` implementation. The existing #467 L0 record reported a 12-lane feasible ladder but its chain clause expressly narrowed one literal condition; the owner has **not** approved that narrowing. An accepted design must preserve required name/delta placement before semantic routing and the no-crossing rule.
- Remote branch `wip/issue-467-lane-rows` at `0a035c64` is reviewable but unmerged. Its post-geometry-fix remeasurement, recorded in the latest issue comments, reports 13 lanes on each of 02/11/12, with 2/24, 1, and 2 dependency relations suppressed. Six focused lane geometry/routing tests pass. A fresh read-only in-memory trace of `station-comms` and `launch-leop` on that exact commit found 16/16 candidate routes for each, all rejected by `relation_route_quality` rather than egress collision; this cause attribution is provisional until reproducible evidence is published. This branch uses View v0.26, already occupied by published `main`; its result is a design input, not release evidence. The reason for the thirteenth lane and default/preset regressions remain unverified.
- In current HALCYON data, `avionics` actual finish is 2027-04-30 while `bus-test` planned start is 2027-04-29. The selected collision rule makes their simultaneous one-lane placement impossible. The product owner directed this session to **correct HALCYON dates**, not weaken the literal chain criterion. The specific edit and downstream schedule effects require design validation. Preserve recorded actuals and the immutable baseline unless an evidence-backed design explicitly decides otherwise.
- The current WIP is not suitable for an as-is merge: it predates the live View schema and current adjacent contracts, it exceeds the lane limit, and its residual routes are not classified. All product changes must be rebuilt as reviewable slices from current `main` after the design chain below is published.

## Literal issue acceptance

### Issue #467

1. A lane row mode exists. On `02-programme-board` the 26 items occupy at most 12 lanes, with the chain `structure → avionics → bus-test` on one lane.
2. Every packed task and milestone has a visible name on the slide; no `W_LAYOUT_LABEL_SUPPRESSED` for a packed item on any committed slide.
3. Lane assignment is deterministic, and a test shows that one inserted item does not reorder unrelated lanes.
4. Deltas remain visible for packed items that have them.
5. New Views and the packaged presets default to lanes; `automatic` still renders exactly as today.
6. At least three committed slides use lanes (for example `01`, `02` and `06`), and their evidence is reproducible.

### Issue #494

1. On `02-programme-board` (lanes), no relation is suppressed for `egress-collision`, and every remaining suppression is listed with a measured cause.
2. `test_lane_relation_routes_never_cross_a_required_lane_label` still passes on 02, 11 and 12: no route crosses any lane or member label.
3. Lane count and lane membership on 02 are unchanged, or any change is attributed.

The original #467 third-slide suggestion is illustrative, not permission to drop its six literal rows. A release review must repeat all nine rows verbatim and link rendered adapter output, not only Scene data.

## Design questions and architectural review gates

1. **Schedule truth and migration.** Locate the authoritative current plan, actual observations and frozen baseline. Evaluate a minimal scheduling change, its dependency/float consequences, and whether any other contexts or copyable gallery resources depend on the dates. Do not alter historical actuals to satisfy layout. Define which source and generated artifacts change together.
2. **Measured packing and chain.** Attribute the thirteenth lane with measured mark, required-name and delta footprints, actual/baseline overlays and the selected label ladder. Test candidate structural policies against neutral and HALCYON data. Keep group-local stable lane identity, deterministic insertion and the ≤12 bound; do not add HALCYON-coordinate branches or silently suppress names.
3. **Route causes.** Capture machine-readable per-relation causes before choosing a routing change. Distinguish egress collision, bounded search, and quality rejection after the geometry fix. Keep the #466 phase order, shared obstacle inventory and no required-label crossings. If a route-aware label/port/gutter change is necessary, assign it to Layout and quantify lane-membership impact under #494 row 3.
4. **Adjacent contracts.** Re-review Specifications 06, 08, 24, 33, 38, 44 and 50, #466 obstacle/route priority, #486 attached milestone semantics, #480 text-driven row extents, #481 group bands, #487 table allocation, #440 key-row, #479 generic preset vocabulary, and #488 lane containment. View selects row intent; Layout completes lane geometry and routes; Scene only projects; adapters serialize.
5. **Version and migration.** Select the next free View schema only after checking published `main` at implementation time. Preserve every live v0.26 field and explicit `automatic` behavior. Include all resource mirrors, conformance fixtures, packaged presets and generated public evidence in an atomic migration; no half-valid catalogue state.

## Design sequence, evidence, and publication

1. Publish this refreshed design plan with all literal rows and the owner-selected data correction direction. No lane product code or HALCYON resource change is authorized by this plan alone.
2. Reproduce the remote WIP measurements in isolation. Record the exact thirteen-lane cause and named residual route causes; run a non-product scheduling probe for the proposed date change and compare current-plan, actual and baseline semantics. Treat unmerged branch data as provisional. If necessary, publish this as a stand-alone feasibility record before finalizing the design.
3. Publish a design correction and whole-architecture review that select the schedule change, lane/route response, version/migration boundaries, diagnostics and evidence policy. Update Specification 38 and any other living authority if semantics or ownership change. Supersede the obsolete L0 narrowing explicitly; do not silently edit historical records.
4. Publish an implementation-plan amendment with small independent slices: source-data/resource evidence; View v0.27-or-next schema and lane contract; Layout packing/route cause correction; defaults/presets and at least three public slides; acceptance review. Each slice names owned files, focused tests, output diff batch, CI/reproduction gate and publication boundary. If the measured ≤12 threshold still fails, return to design rather than merging the WIP.

Before any push, fetch and compare remote `main`; publish serially. CI supplies the full three-OS pytest/conformance and newest-Python materializer gate; locally use a project `.venv` for focused checks. Leave reviewer-maintained #454 untouched.

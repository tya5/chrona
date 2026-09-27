# Current work plan — closed lane projection (#467, #494)

**Normative design:** Specs [38](../../specification/38-review-row-composition.md) and [46](../../specification/46-completed-scene-paint.md). Public lane mode stays fail-closed until B2/B3 and activation gates. Lane count follows measured geometry and the chain rule, not a numeric target.

## B2 architecture decision

Layout derives one immutable plan and completed geometry. Scene projects its
primitives and checks a lane-only member inventory against their tags; adapters
serialize it. The read-only rule audit uses the closed Scene. Scene v0.6 adds
optional lane fields without changing automatic/explicit bytes. B2 tests reject
missing, extra, or untagged member primitives. Spec 38 owns the detailed rule.

| Publishable slice | Files/owners and migration | Focused acceptance and evidence |
| --- | --- | --- |
| **S2b-1 shared frame extraction** | `layout/surface_composer.py`, shared Layout mark-geometry module, `layout/presentation.py`, focused Layout tests. Introduce `MarkBandFrame` and one placement composer; automatic/explicit pass their existing track frames, lanes pass zero-origin mark band. No schema/resource change. | Characterize planned, snapshot, Actual/open Actual, point/glyph/icon, progress, ports and symbols before/after extraction. Exact automatic/explicit Scene/SVG bytes, local-frame bounds/ports and one-translation tests. Publish with guard closed. |
| **S2b-2 typed closure and validation** | `layout/lane_allocation.py`, `layout/lane_preflight.py`, typed facet/label projection records and tests. Add expected-emission inventory, canonical instance/member/primitive identities, symbol/progress/plain-mark payloads, icon group cardinality and stroke validation, exact attached host resolution, pairwise overlay compatibility. No View schema change. | Missing/duplicate facets, stack-vs-shared comparison, glyph paint order, icon vector/raster payload, progress clip, attached/repeated source, unsupported folded point and unknown required primitive fail closed. Complete local payload and port/footprint checks pass. Publish independently. |
| **S2b-3 mapper and immutable preflight** | New Layout mapper and `lane_preflight.py`, View/normalized projection adapters only for selected facts, tests. Retain exact candidate/facet/required-label closure, `as_of`, seed frame and Theme/font/scale identities; preflight allocates once. | Planned/comparison/Actual/open/point/progress/icon/labelVisual fixtures, missing-placement diagnostics, same-plan and cutoff mismatch tests. No silent omission; all countable member IDs biject with allocation. Batch public materializers once for S2b-1..3 and compare generated Scene/SVG/diagnostics; automatic bytes unchanged. Publish/review with guard closed. |
| **B2 one-plan realization** | Layout request/result, `surface_composer.py`, table/group/row solve, Scene model/projection/serialization and v0.6 schema, `usecases/render_review.py`, tests. Consume the exact plan; translate local closure once through lane mark-band anchor; emit one Scene primitive per expected non-icon facet and one ICON per complete icon group. Populate lane-only surface mode and member/primary-mark primitive inventory from that same plan. | Direct hidden 02 composition, exact chain, names/deltas/icons, lane table/group extents, seed/final frame and cutoff identity. Scene rejects missing/extra/untagged inventory primitives; then a read-only Scene checker proves pairwise non-redundancy and reports each group's primary-mark lower bound. Test insertion stability and automatic bytes. Publish with public guard closed. |
| **B3 and L3c release** | Follow the [rule-based L3 implementation plan](issue-467-494-rule-based-lane-acceptance-implementation-plan-2026-09-27.md). B3 proves route causes/non-crossing. L3c migrates defaults/presets/three committed slides and generated mirrors atomically. | Batch affected public materializers and SVG/Scene visual diffs. CI supplies planned full three-OS pytest/conformance, wheel/smoke and newest-Python materializer evidence. No issue closure until every literal criterion below has direct public evidence and acceptance review. |

If any extraction reveals a changed formula, unexpected output, missing semantic role or Scene-side geometry decision, stop that slice, publish a design correction/whole-architecture review and amend this plan before resuming. For every publication: focused local tests, diagnostic inventory where changed, fetch `origin/main`, inspect staged/generated diff and ahead/behind, push serially without force, verify remote commit, then inspect one material CI run without busy polling.

## Literal #467 acceptance

1. A lane row mode exists. On `02-programme-board` the chain `structure → avionics → bus-test` is on one lane, and the lane count is **justified by the rule, not by a target number**. Both checks read the Scene footprints (marks, comparison marks, names, deltas, icons):
   - **No redundant lane.** For every pair of lanes in the same group, moving all items of one into the other would make two footprints collide. The only exception is a pair kept apart by the chain rule, and those pairs are listed.
   - **Lower bound reported.** For each group, report the maximum number of footprints that overlap at one date, next to its lane count, and attribute any difference. The lower bound is reported and explained; it is not a target.
2. Every packed task and milestone has a visible name on the slide; no `W_LAYOUT_LABEL_SUPPRESSED` for a packed item on any committed slide.
3. Lane assignment is deterministic, and a test shows that one inserted item does not reorder unrelated lanes.
4. Deltas remain visible for packed items that have them.
5. New Views and the packaged presets default to lanes; `automatic` still renders exactly as today.
6. At least three committed slides use lanes (for example `01`, `02` and `06`), and their evidence is reproducible.

## Literal #494 acceptance

1. On `02-programme-board` (lanes), no relation is suppressed for `egress-collision`, and every remaining suppression is listed with a measured cause.
2. `test_lane_relation_routes_never_cross_a_required_lane_label` still passes on 02, 11 and 12: no route crosses any lane or member label.
3. Lane count and lane membership on 02 are unchanged, or any change is attributed.

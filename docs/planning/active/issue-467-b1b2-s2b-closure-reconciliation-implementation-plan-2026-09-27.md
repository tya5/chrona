# Implementation Plan Amendment — S2b closed lane projection (#467, #494)

**Public design base:** `a02ccc03d8bc5b5b2187402b10f4ca495220b156`. **Authority:** [design plan](issue-467-b1b2-s2b-closure-reconciliation-design-plan-2026-09-27.md), [selected correction](../../design/issue-467-b1b2-s2b-closure-reconciliation-correction-2026-09-27.md), [architecture review](../../reviews/current/issue-467-b1b2-s2b-closure-reconciliation-architecture-review-2026-09-27.md), Specs [38](../../specification/38-review-row-composition.md) and [46](../../specification/46-completed-scene-paint.md). Supersedes S2b/B2 assumptions in the older [facet-count implementation plan](issue-467-b1b2-facet-count-asof-implementation-plan-amendment-2026-09-27.md), not its historical record. Public lane mode stays fail-closed until B2/B3 and activation gates. No fixed 12/14 lane ceiling, above-ten quota or compulsory third label row.

## Current B2 design and architecture review (2026-09-27)

A read-only Scene audit cannot identify an untagged lane primitive from optional
primitive tags alone: automatic/explicit primitives are legitimately untagged.
The selected correction is a lane-only `SceneSurface` mode discriminator plus
typed member inventory (row/member IDs, emitted primitive IDs, primary-mark
IDs). B2 derives it from the immutable Layout plan. Scene validates exact
inventory↔tagged-primitive correspondence and rejects untagged lane-bearing
purposes. The checker then reads the closed Scene, not Layout-only data. This
keeps Project/View semantics upstream, geometry in Layout, structural identity
in Scene, and adapters as serializers. Optional fields extend Scene v0.6 only
for lane surfaces; automatic/explicit bytes stay unchanged. No new View syntax
or Theme policy is needed. This resolves the completeness gap without spatial
or `source_ref` inference. [Spec 38](../../specification/38-review-row-composition.md)
is the normative authority; B2 tests must prove missing/extra/untagged member
primitives fail before the #467 Scene rule audit.

| Publishable slice | Files/owners and migration | Focused acceptance and evidence |
| --- | --- | --- |
| **S2b-1 shared frame extraction** | `layout/surface_composer.py`, shared Layout mark-geometry module, `layout/presentation.py`, focused Layout tests. Introduce `MarkBandFrame` and one placement composer; automatic/explicit pass their existing track frames, lanes pass zero-origin mark band. No schema/resource change. | Characterize planned, snapshot, Actual/open Actual, point/glyph/icon, progress, ports and symbols before/after extraction. Exact automatic/explicit Scene/SVG bytes, local-frame bounds/ports and one-translation tests. Publish with guard closed. |
| **S2b-2 typed closure and validation** | `layout/lane_allocation.py`, `layout/lane_preflight.py`, typed facet/label projection records and tests. Add expected-emission inventory, canonical instance/member/primitive identities, symbol/progress/plain-mark payloads, icon group cardinality and stroke validation, exact attached host resolution, pairwise overlay compatibility. No View schema change. | Missing/duplicate facets, stack-vs-shared comparison, glyph paint order, icon vector/raster payload, progress clip, attached/repeated source, unsupported folded point and unknown required primitive fail closed. Complete local payload and port/footprint checks pass. Publish independently. |
| **S2b-3 mapper and immutable preflight** | New Layout mapper and `lane_preflight.py`, View/normalized projection adapters only for selected facts, tests. Retain exact candidate/facet/required-label closure, `as_of`, seed frame and Theme/font/scale identities; preflight allocates once. | Planned/comparison/Actual/open/point/progress/icon/labelVisual fixtures, missing-placement diagnostics, same-plan and cutoff mismatch tests. No silent omission; all countable member IDs biject with allocation. Batch public materializers once for S2b-1..3 and compare generated Scene/SVG/diagnostics; automatic bytes unchanged. Publish/review with guard closed. |
| **B2 one-plan realization** | Layout request/result, `surface_composer.py`, table/group/row solve, Scene projection/serialization, `usecases/render_review.py`, tests. Consume the exact plan; translate local closure once through lane mark-band anchor; emit one Scene primitive per expected non-icon facet and one ICON per complete icon group. | Direct hidden 02 composition, exact chain, names/deltas/icons, lane table/group extents, seed/final frame and cutoff identity; read-only Scene pairwise non-redundancy and per-group primary-mark lower-bound report; insertion stability and automatic bytes. Scene v0.6 lane provenance only. Publish with public guard closed. |
| **B3 and L3c release** | Follow the [rule-based L3 implementation plan](issue-467-494-rule-based-lane-acceptance-implementation-plan-2026-09-27.md). B3 proves route causes/non-crossing. L3c migrates defaults/presets/three committed slides and generated mirrors atomically. | Batch affected public materializers and SVG/Scene visual diffs. CI supplies planned full three-OS pytest/conformance, wheel/smoke and newest-Python materializer evidence. No issue closure until every literal criterion below has direct public evidence and acceptance review. |

If any extraction reveals a changed formula, unexpected output, missing semantic role or Scene-side geometry decision, stop that slice, publish a design correction/whole-architecture review and amend this plan before resuming. For every publication: focused local tests, diagnostic inventory where changed, fetch `origin/main`, inspect staged/generated diff and ahead/behind, push serially without force, verify remote commit, then inspect one material CI run without busy polling.

## Literal #467 acceptance

1. A lane row mode exists. On `02-programme-board` the chain `structure → avionics → bus-test` is on one lane, and the lane count is **justified by the rule, not by a target number**. Both checks read the Scene footprints (marks, comparison marks, names, deltas, icons):
   - **No redundant lane.** For every pair of lanes in the same group, moving all items of one into the other would make two footprints collide. The only exception is a pair kept apart by the chain rule, and those pairs are listed.
   - **Lower bound reported.** For each group, report the maximum number of footprints that overlap at one date, next to its lane count, and attribute any difference. The lower bound is reported and explained; it is not a target.
   *(Amended 2026-09-27 twice: "at most 12" and then "at most 14" were arbitrary numbers and are withdrawn; see the comments.)*
2. Every packed task and milestone has a visible name on the slide; no `W_LAYOUT_LABEL_SUPPRESSED` for a packed item on any committed slide.
3. Lane assignment is deterministic, and a test shows that one inserted item does not reorder unrelated lanes.
4. Deltas remain visible for packed items that have them.
5. New Views and the packaged presets default to lanes; `automatic` still renders exactly as today.
6. At least three committed slides use lanes (for example `01`, `02` and `06`), and their evidence is reproducible.

## Literal #494 acceptance

1. On `02-programme-board` (lanes), no relation is suppressed for `egress-collision`, and every remaining suppression is listed with a measured cause.
2. `test_lane_relation_routes_never_cross_a_required_lane_label` still passes on 02, 11 and 12: no route crosses any lane or member label.
3. Lane count and lane membership on 02 are unchanged, or any change is attributed.

# Implementation Plan Amendment — Fourteen-lane gate and cause inventory (#467, #494)

**Supersedes the numeric gate and L3b pause text** in the [L3 completion ladder](issue-467-494-l3-lane-completion-publication-amendment-2026-09-27.md), [B1b-2 implementation amendments](issue-467-l3b-candidate-footprint-implementation-amendment-2026-09-27.md) and earlier active plans. **Design:** [owner-amendment correction](../../design/issue-467-494-lane-count-acceptance-correction-2026-09-27.md). **Architecture review:** [whole-architecture check](../../reviews/current/issue-467-494-lane-count-acceptance-architecture-review-2026-09-27.md). **Normative authority:** Specs [38](../../specification/38-review-row-composition.md), [46](../../specification/46-completed-scene-paint.md), and [50](../../specification/50-constraint-driven-gantt-surface-quality.md). **Public design base:** `5aebcccb44730015c744190a2ec17067d7d3edfc`.

## Early feasibility and remaining risk

The remote WIP `0a035c64` generated 02 Scene has 13 lanes for 26 items, so a two-row label ladder can meet the amended numeric ceiling. It does **not** meet the named chain: `structure` and `avionics` share `lane:bus:structure`, while `bus-test` is on `lane:bus:bus-test`. Its two remaining route suppressions name `station-comms` and `launch-leop` but lack measured causes. That branch predates the published 4wd Project, View v0.27, current icon/stroke footprint and S2 facets; it is neither current-main acceptance nor a merge target. The third label row is not needed to pass the numeric ceiling. Current-main B2/B3 measurement remains decisive.

## Independent publication units

| Unit and owners | Focused verification and generated evidence | Acceptance and publication boundary |
| --- | --- | --- |
| **S2b projection mapper/preflight** — `src/chrona/presentation/layout/` mapper/allocator helpers and focused unit/integration fixtures; no Scene/adapter lane activation. | Map the closed ReviewProjection to one countable root/attached bundle with source-keyed comparison/Actual/progress/icon facets, completed Theme/scale geometry, measured required labels and 10× stroke footprint. Test explicit `as_of`, open Actual cutoff, facet/port identity, missing-geometry diagnostics, seeded automatic byte parity. Run focused tests and the public-materializer check as one batch. | Review/publish independently while lane mode stays fail-closed. No hard-coded 12/14 threshold or forced third row. A missing ownership rule returns to design before code. |
| **B2/L3b one-plan composition** — `surface_composer.py`, typed Layout request/result, lane table/row/group helpers and focused composer tests. | Use current 4wd Project/View v0.27. Materialize hidden/direct 02 lane composition first: exact 26 countable items, ≤14 lanes, chain on one lane, required name/delta visibility, no packed-name suppression, stable insertion, table cells/group bands, and a source-keyed cause for each lane beyond ten. Assert one immutable preflight plan drives final placement; compare automatic Scene/SVG bytes. Batch focused 02/11/12 geometry and generated diffs. | Publish independently only with the public lane guard closed. Pause on >14 lanes, broken chain, missing above-ten cause, text suppression, layer leak or unstable inline geometry; return to design and whole-architecture review before proceeding. Do not force a third row merely to lower count. |
| **B3/#494 route-cause closure** — Layout shared obstacle/routing result and typed cause transport, Scene projection only where required, focused route tests. | On direct 02/11/12 lane composition, check zero 02 `egress-collision` suppressions, list measured causes for every other suppression, and run `test_lane_relation_routes_never_cross_a_required_lane_label`. Attribute exact 02 lane membership differences; inspect route/label geometry as one generated batch. No endpoint-label exemptions or loosened quality bounds. | Publish and review independently with public lane mode still guarded. Any crossing, unknown cause or unexpected membership returns to design before activation. |
| **L3c activation/resource migration** — View defaults/preset YAML and mirrors/pins, HALCYON 01/02/third compatible slide, gallery evidence and regenerated Scene/SVG/PNG; adapter code only if an approved interface demands it. | Change packaged presets and defaults atomically, retaining Editorial reference in separate gallery identity. Run focused tests, public materializer batch, generated Scene/SVG/PNG diff and visual check, bare-default/starter checks; let CI supply three-OS full pytest/conformance/wheel and newest-Python materializers. | Publish only when all literal #467/#494 criteria pass on rendered public artifacts. No temporarily unmaterializable default. Then publish issue acceptance review with exact commits, CI and every criterion; keep issues open until release evidence is green. |

## Literal acceptance table to carry into release review

### #467

1. A lane row mode exists. On `02-programme-board` the 26 items occupy **at most 14 lanes**, with the chain `structure → avionics → bus-test` on one lane. The acceptance review lists the lane count and attributes every lane above 10 to its cause: a mark or label collision, or a chain rule. *(Amended 2026-09-27: was "at most 12"; see the comment.)*
2. Every packed task and milestone has a visible name on the slide; no `W_LAYOUT_LABEL_SUPPRESSED` for a packed item on any committed slide.
3. Lane assignment is deterministic, and a test shows that one inserted item does not reorder unrelated lanes.
4. Deltas remain visible for packed items that have them.
5. New Views and the packaged presets default to lanes; `automatic` still renders exactly as today.
6. At least three committed slides use lanes (for example `01`, `02` and `06`), and their evidence is reproducible.

### #494

1. On `02-programme-board` (lanes), no relation is suppressed for `egress-collision`, and every remaining suppression is listed with a measured cause.
2. `test_lane_relation_routes_never_cross_a_required_lane_label` still passes on 02, 11 and 12: no route crosses any lane or member label.
3. Lane count and lane membership on 02 are unchanged, or any change is attributed.

## CI and publication discipline

Each unit gets focused local tests and one batched public-materializer/generated-diff pass; do not rerun all SVGs for each small fixture. At a material push inspect the resulting CI once its run completes rather than polling repeatedly. Before each serial push, fetch `origin/main`, confirm exact ahead/behind and staged/generated diff, and stop on non-fast-forward or unexpected remote updates. A passing test is not a substitute for geometry, rendered-slide and architecture review.

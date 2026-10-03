# Issue #1060: relation entry `side`, back-route abutting chains through the row gap (work record)

Living record for [#1060](https://github.com/tya5/chrona/issues/1060) (owner-approved, target B of #987): baseline, design plan, design, architecture review and implementation plan, published together before any code. Edited in place; Git keeps history. It builds on the #1030 entry policy (work record `issue-1030-relation-entry-side-2026-10-03.md`) and the #1059 route invariant (no route overlaps itself; PR #1069). The target is the approved mock `docs/research/presentation/halcyon-1-target-design-2026-09-21/board/02-programme-board.png`.

**Scope rule (owner):** a new Layout Profile value and its own evidence; the reviewer's `examples/halcyon-1/*target-b*` files are not edited (adopting `entry: side` there is the reviewer's step). Another agent works in the same routing and terminal code (#1042, #1046, #1044): diffs stay minimal and the new path is built from plain orthogonal points.

## 1. Published baseline

Read on `d4b081cf` (code, the issue's mock rule, committed images):

1. **What `side-when-free` does.** `ports.connector_egress_candidates` offers a horizontal stub candidate only when the target is a span, the endpoint is `start` (or `end`) and the source's nominal port lies strictly on the approach side of the mark. A point (gate) target gets none. Otherwise the nearest-port order applies and the route often ends vertically on the bar corner.
2. **Abutting chains.** On target B 11 of 25 paths end vertically; in each the source end is at or after the target start (finish-to-start with no gap), so no stub candidate exists.
3. **The mock's rule** (issue text, `render_mocks.py draw_deps`): with room (`start - 6 >= end + 4`) out, across, down, in; otherwise leave the source end, step out 6, run vertically to the gap between the rows just before the target row, travel back to `start - 6`, drop to mid height and enter the start: 4 bends, arrowhead along the bar.
4. **Machinery.** Candidate pairs are tried in order by `surface_routes.compose_surface_routes` (flat rows) and `routing.select_lane_relation_route` (lane rows); both use `relation_route_quality` (`maxBends`, `maxDetourRatio`) and, since #1059, reject a self-overlapping route. Row geometry is available to `compose_surface_routes` (`rows`, `groups`); obstacle checks (`egress_collisions`, `collisions`) are the existing corridor and collision tests; other relations' routes are not obstacles (crossing is allowed today).
5. **Diagnostics.** Info diagnostics such as `I_LAYOUT_LANE_ROUTE_CAUSE` already travel in the Scene `diagnostics` list.

Unverified: how many committed slides change with `entry: side` as a global value (measured in slice S2 with images read); how the back-route behaves across group header bands and for targets several rows below the source.

## 2. Literal acceptance (copied from #1060)

Synthetic fixtures, checked on the published Scene: abutting finish-to-start (source end == target start); overlapping (source end > target start); target row below the source and above it; a mirrored `end` endpoint; a gate target; the row-gap corridor blocked by a label or mark (falls back, with a diagnostic); the back-route exceeding `maxBends` (falls back). For each:

| # | Criterion |
| --- | --- |
| B1 | When a back-route fits, the last segment is horizontal at the target's mid height and points into the start (or end). |
| B2 | The horizontal leg of the back-route lies in the row gap, outside every row's mark band. |
| B3 | The path has at most `maxBends` bends and no self-reversing triple (#1059). |
| B4 | No crossing of marks or text. |
| B5 | `side-when-free` and `any` outputs are byte-identical to today's (the new value only). |
| B6 | On target B with `entry: side`, regenerated, the 11 paths enter from the side unless a diagnostic explains a fallback. |

## 3. Design plan

Use cases (synthetic Projects; target B is evidence, never the oracle): **U1** abutting FS, target row below; **U2** overlapping FS (source end after target start); **U3** target row above the source; **U4** mirrored `end` endpoint; **U5** gate target; **U6** corridor blocked; **U7** back-route over `maxBends`.

Open decisions: how the back-route is built and ordered; what "row gap" means; the exit stub; gates; the fallback diagnostic; point sources.

## 4. Design

| Decision | Choice | Why / alternatives rejected |
| --- | --- | --- |
| Value | `relationRouting.entry: side` added to the existing enum (optional property, additive; Spec 56 section 3.2; default stays `side-when-free`). | The issue declares it; no new property. |
| Order | For a target `start` (or `end`): 1. the `side-when-free` candidates unchanged (forward side entry, with the #1059 repair); 2. **only when the source does not lie strictly on the approach side** (no forward candidate exists, the abutting and overlapping cases) the back-route; 3. the existing order. A back-route that is blocked, over `maxBends` or `maxDetourRatio`, or fails the #1059 invariant falls to 3. | The back-route is the answer to exactly the case the forward rule excludes; where a forward candidate exists and fails, the old order is the documented fallback. |
| Shape | A complete orthogonal path built directly, not searched: source port `P0`; exit stub `P1 = P0 + e` away from the source mark along its endpoint's outward direction (`end`: right, `start`: left); vertical to the **gap line** `P2 = (P1.x, g)`; across to the entry tip `P3 = (tip.x, g)` where `tip` is the #1030 stub tip (`start - stub`, mirrored for `end`); `P4 = (tip.x, y_target)`; the target port. Degenerate legs collapse (fewer bends). 4 bends at most. Stubs: entry stub as #1030 (`headLength` + max(corner radius, stroke width)); exit stub equals the same clearance. | Search would pick shapes the issue excludes (arrival from the stub side, #1059); the mock fixes the shape. |
| Gap line | The boundary line of the target row on the source's side: the target row's top edge when the target row is below the source row, its bottom edge when above (the mock's `B.y - step`, `step = row height / 2`). Same row: no gap, no back-route (falls to 3). The line lies between row bands, so it is outside every row's mark band by construction; the collision checks run against marks, text, labels and group header bands. | A row boundary needs no new geometry owner: `compose_surface_routes` already holds the row and group bounds. |
| Gates | In `side` only, a point (gate or milestone) target with endpoint `start` or `at` gets the horizontal candidate at its left vertex (mirror: right vertex for `end`), with the same stub rule; point sources use their existing ports. In `side-when-free` and `any` points stay unchanged (B5). | Keeps B5 byte identity while giving gates the mock's entry. |
| Fallback diagnostic | When `entry: side` is declared and the selected route does not end horizontally into the start or end, Layout appends the info diagnostic `I_LAYOUT_RELATION_ENTRY_FALLBACK:<scene relation id>` (no change to the route). Registered with a warning-free sentence like the other `I_` diagnostics. | The issue asks that the fallback is visible; an info finding does not fail conformance. |
| Lane rows | The same builder is used before `select_lane_relation_route`; an accepted back-route is returned as the selection, otherwise the candidate pairs run unchanged. | One rule in both row modes. |

## 5. Architecture review

- **Layers.** Intent is a Layout Profile enum value; Layout builds the path and checks obstacles; Scene carries the path and the info diagnostic; adapters unchanged. No View, Theme or Project change.
- **Invariants.** The built path is checked by `relation_route_quality` including the #1059 overlap rule, then obstacle-checked per segment (host marks exempt only at the endpoints, as for corridors).
- **Rounded corners (#1046) and terminals (#1042/#1044).** The path is plain orthogonal points with one more or fewer vertices; those features consume points unchanged.
- **Compatibility.** `any` and `side-when-free` are byte identical (proved by `regenerate_public_examples --check` before and after); the schema change is an enum value (`schema_equivalence` run, expected delta recorded if the gate lists it as widening).
- **Corpus discipline.** The synthetic fixtures carry the rule; target B and the corpus are evidence against the mock and #575; no corpus datum is edited.
- **Residual risks.** A long vertical at `P1.x` may cross intermediate rows' marks (blocked then falls back); overlapping other relations' segments follows today's crossing rules; group header bands between rows may make the gap line collide (falls back).

## 6. Implementation plan

| Slice | Content | Files | Evidence and gate |
| --- | --- | --- | --- |
| S1 | Enum value, path builder, order, gate stub, diagnostic | `schemas/layout-profile-v0.10.schema.yaml` (enum + description), `layout/ports.py` (point-target stub in `side`), `layout/surface_routes.py` and `layout/routing.py` (builder and lane hook), `usecases/diagnostic_messages.py`, Spec 50 section 3.3 | Synthetic tests U1 to U7 under `side`, plus `side-when-free`/`any` unchanged; mutation checks; `regenerate_public_examples --check` PASS; `schema_equivalence`; conformance |
| S2 | Corpus experiment | none | `entry: side` as the global value on all slides, before/after images read, honest comparison with the mock, record here |
| Review | Literal acceptance review (`chrona:literal-acceptance/v1`), B6 shown by the reviewer's adoption or by the experiment | `docs/reviews/current/` | exact-commit three-OS run |

Publication boundary: this record alone is the design PR; S1 is one code PR.

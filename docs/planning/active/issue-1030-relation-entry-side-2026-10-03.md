# Issue #1030: relation entry side, enter a start horizontally when the corridor is free (work record)

Living record for [#1030](https://github.com/tya5/chrona/issues/1030) (successor of #991 item 15, target B of #987): baseline, design plan, design, architecture review and implementation plan, published together before any code. Edited in place; Git keeps history. The target is the owner-approved mock `docs/research/presentation/halcyon-1-target-design-2026-09-21/board/02-programme-board.png`.

**Scope rule (owner, 2026-10-03):** this adds a Layout Profile policy and its own evidence (synthetic tests, a corpus experiment). It does not edit the reviewer's `examples/halcyon-1/*target-b*` files; adopting the policy there is the reviewer's step and not an acceptance row. It avoids the comparison/ghost/hatch files that #991's open PRs touch.

## 1. Published baseline

Read on `14892b4e` (code and committed images; nothing inferred):

1. **Candidate order.** `layout/ports.py: connector_egress_candidates` returns, for a span endpoint, four candidates `end, start, above, below` whose semantic port is the temporal edge (`mark.start_port` or `end_port`) and whose exposed port is the cluster edge on that side. They are sorted by the Manhattan distance of the exposed port from `toward` (the other endpoint's nominal port), ties `end, start, above, below`. For a source up and to the left of the bar, `above` (the top-left corner) is nearer than `start` (left edge, mid height), so the line drops onto the corner and the arrowhead lies half outside the bar. The `start` candidate has no corridor (`semantic == exposed`).
2. **Selection.** `surface_routes.compose_surface_routes` tries source and target candidate pairs in order and takes the first pair whose corridors are collision free, whose route search succeeds and whose route passes `relation_route_quality` (`maxBends`, `maxDetourRatio`). Lane rows use `select_lane_relation_route` with the same pair order. A failed candidate falls to the next, so reordering never makes a relation unroutable that was routable.
3. **Policy home.** Layout Profile `relationRouting` holds `maxBends` and `maxDetourRatio` (both required) in `schemas/layout-profile-v0.10.schema.yaml`; `engine.solve_layout` copies them onto `LayoutManifest.relation_*`; Specification 50 section 3.3 describes routing.
4. **Terminal size.** The relation terminal marker (`relationTargetTerminal`, `marker_geometry`) has `headLength`; `timeline.relation.cornerRadius` is a Theme metric.
5. **Evidence.** On `halcyon-1/target-b` (#1031 fixed) `pdr -> structure`, `structure -> avionics` and `eps -> avionics` enter from above at the bar's top-left corner; the mock enters horizontally at mid-height.

Unverified: how many committed slides change if horizontal entry were the default (measured in slice S2, images read); whether a stub that clears the arrowhead leaves a readable run in the narrowest real gap.

## 2. Literal acceptance (copied from #1030)

The issue has no acceptance table; its literal asks are:

| # | Ask |
| --- | --- |
| A1 | When the endpoint is `start` (or the mirrored `end`), the source lies on the approach side, the space immediately beside the endpoint at mid-height is free and a stub of at least arrowhead plus clearance fits, try the horizontal entry first; otherwise keep today's order. |
| A2 | A declared policy (for example `relationRouting.entry: side-when-free \| any`), default chosen on readability grounds. |
| A3 | Both branches tested on synthetic fixtures: source left with free space, source right, blocked corridor, narrow gap needing one more bend. |
| A4 | Corpus-wide diffs reviewed against #575. |

## 3. Design plan

Use cases (synthetic Projects; target B is evidence, never the oracle): **U1** a dependency whose source is up-left of the target bar enters the start horizontally; **U2** the same with the source right of an `end` endpoint (start-to-start and finish-to-finish relations enter the mirrored side); **U3** a neighbouring bar or label in the stub space keeps today's order; **U4** a gap too narrow for arrowhead plus clearance keeps today's order; **U5** the horizontal entry needs one more bend than the drop, still within `maxBends`.

Open decisions: the policy name and values; its default; what "free" means; the stub length; whether the source side is mirrored.

## 4. Design

| Decision | Choice | Why / alternatives rejected |
| --- | --- | --- |
| Policy | Optional `relationRouting.entry`: `any` or `side-when-free`. Absent means `any`, today's order byte for byte (Spec 56 section 3.2: an optional property is added in place, no version bump; the consumer supplies the omission behaviour and tests it; a schema `default` implements nothing). Added to the schema as a named `$defs` enum, not a repeated literal. | A boolean hides the closed vocabulary; a per-relation View property is a View schema change for a pure routing preference, and the issue asks for a Layout policy. |
| Default (owner-level call) | `any` in slice S1, so no committed slide changes and the reviewer adopts `side-when-free` for target B on its own YAML. Flipping the default is a separate slice S2 decided only after the corpus experiment images are read. Reverse: change one `engine.py` default and regenerate. | The issue says the change moves every slide with relations; shipping the knob first keeps the first merge byte-neutral and lets the reviewer decide with images. |
| Where | Entry preference is a candidate-order rule in `layout/ports.py` (`connector_egress_candidates` gains `entry` and `stub_free`), fed by `surface_routes` and the lane router. Layout owns it; Scene, View, Theme and adapters are untouched. | Reordering in the route search would duplicate the pair loop; the candidate list is the single place where order is decided today. |
| Rule | For the **target** endpoint `start` with the source nominal port left of the mark's left edge (mirror: endpoint `end`, source right of the right edge), and a collision-free stub, the horizontal candidate (`start`, or `end` for the mirror) moves first; the other candidates keep their order after it. In every other case the order is unchanged. Source endpoints keep today's order (the issue concerns entering a start). Points and `at` endpoints (diamonds) are unchanged. | The ask names `start` and the mirrored `end` only. |
| Free | The stub is the segment from the exposed port, away from the mark, of length `headLength + clearance` at the endpoint's mid height, where `clearance = max(timeline.relation.cornerRadius, relation stroke width)` (the straight run a rounded corner and the arrowhead need). It is free when `obstacles.egress_collisions` with the same classes the corridor check uses (`mark`, `text`, `label-visual`, regions `timeline`, `group-header`) finds nothing, host marks exempt. No new metric or knob: both numbers come from the Theme the relation already resolves. | A fixed pixel constant would not follow a Theme's terminal size. |
| Failure | If the horizontal candidate then fails route search or `relation_route_quality`, the loop continues to the remaining candidates exactly as today; a relation routable today stays routable. | Order only; no new rejection. |
| Extra bend (U5) | Accepted when `maxBends` and `maxDetourRatio` accept it; those limits stay the readability bound. | A separate bend penalty would be a second knob. |

Diagnostics: none new. Specification 50 section 3.3 gets the policy and the rule (the issue record points to it).

## 5. Architecture review

- **Layers.** Intent is a Layout Profile property; Layout reorders ports and routes; Scene carries the completed path; adapters serialize. The rule needs obstacles, so it is evaluated in `surface_routes`/the lane router, not in `ports.py` alone: `ports.py` stays obstacle-free and receives a precomputed `stub_free` predicate.
- **Determinism.** The order is a pure function of geometry and the policy; ties keep the existing order.
- **Schema.** `layout-profile-v0.10` gains one optional property; `python -m tools.schema_equivalence --base-rev origin/main` is run and recorded in the PR; resource mirrors of the schema are committed with it.
- **Compatibility.** Absent or `any` is byte identical, proven by `regenerate_public_examples --check` before and after S1.
- **Corpus discipline.** The synthetic fixtures carry the rule; the corpus experiment (S2) is evidence against the target mock and #575, not an oracle, and no corpus datum is edited.
- **Residual risks.** A horizontal entry can cross a neighbouring route that the drop avoided (route search owns crossings; the quality ranking is unchanged); lane rows use a separate selector (`select_lane_relation_route`) that must receive the same order.

## 6. Implementation plan

| Slice | Content | Files | Evidence and gate |
| --- | --- | --- | --- |
| S1 | Policy, rule and tests; default `any` | `schemas/layout-profile-v0.10.schema.yaml` (+ mirrors), `layout/engine.py`, `layout/model.py` (`relation_entry`), `layout/ports.py`, `layout/surface_routes.py`, lane router call site, Spec 50 section 3.3 | Synthetic tests for U1 to U5 under both policy values, mutation-checked; `regenerate_public_examples --check` byte identical; `schema_equivalence` result in the PR; conformance |
| S2 | Corpus experiment, default decision | none by default; a flip edits `engine.py` only | Render every relation slide with `side-when-free`, read before/after images of each changed slide, compare with the mock and #575, record the default decision and whether to flip |
| Review | Literal acceptance review (`chrona:literal-acceptance/v1`) | `docs/reviews/current/` | Exact-main three-OS run on the review commit; successor issues for any deferred row |

Publication boundary: this record alone is the design PR; S1 is one code PR; S2 evidence goes in the work record and, if the default flips, in its own PR.

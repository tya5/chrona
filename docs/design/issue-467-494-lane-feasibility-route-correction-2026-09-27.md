# Design Correction — Lane Feasibility and Route Evidence (#467, #494)

**Corrects:** the lane label ladder and chain clauses in the [L0 ladder correction](issue-467-lane-rows-l0-ladder-correction-2026-09-27.md), and updates the [phase/version correction](issue-467-lane-rows-phase-and-version-correction-2026-09-27.md). **Evidence:** [post-geometry feasibility probe](../research/presentation/issue-467-494-post-geometry-feasibility-2026-09-27.md). **Plan:** [recompletion plan](../planning/active/issue-467-494-lane-feasibility-recompletion-design-plan-2026-09-27.md).

## Decisions

### HALCYON schedule and chain

The owner-selected response is a current-plan data correction. Change only the `avionics-bustest` dependency lag in the current HALCYON-1 Project from `2wd` to `4wd`. The 3wd probe still starts bus-test on April 30, the date avionics actually finished, so it does not remove the overlap. At 4wd the planned bus-test interval is May 3–May 17, allowing the marks for `structure`, `avionics`, and `bus-test` to occupy the same lane under the unchanged collision rule.

Do not rewrite the `avionics` actual or the frozen June baseline. The current Project is the scheduling authority for this correction; the baseline remains an immutable comparison record. Regenerate only current-Project-dependent schedule evidence and its dependent rendered artifacts in the implementation slice. The migration review must verify whether any other contexts or copied resources materialize the current Project and update them atomically where required.

### Lane-local label rows

Extend the generic finite label ladder by one stagger level. Keep the existing row-1 and row-2 candidates and add row-3 start-aligned and end-aligned candidates, in that order after the existing candidates. Row 3 is placed in the lane-local band immediately above row 2. The lane footprint reserves each used label row plus the existing row padding; all title/delta measured geometry participates in the same collision checks. Candidate order and tie breaks remain deterministic. If a candidate collides with another mark or required label, try the next candidate; if none fits in an existing lane, open the next stable lane. An item's required name is never suppressed.

This is a bounded, generic Layout policy, not a HALCYON-specific geometry branch or a View field. Lane allocation continues to use measured mark, name, delta, comparison, and point-glyph footprints. The observed third-row experiment required 148.5px for the affected bus lane and yielded ten total lanes, with `pdr, eps, cdr` and `structure, avionics, bus-test` each grouped as reported by the feasibility record. These are feasibility observations, not promised fixed coordinates or universal lane counts.

### Semantic route disposition

Keep the #466 phase order and required-label obstacles. Do not exempt an item's own label, relax route quality bounds, or permit a route through required text. The current third-row probe attributes the three remaining suppressions (`avionics-cdr`, `station-comms`, `launch-leop`) to `relation_route_quality`: 16 of 16 candidates rejected for each, with zero egress-collision rejections. A route with no acceptable candidate remains suppressed under the existing policy.

This disposition is consistent with #494's literal first criterion: it requires zero `egress-collision` suppressions and a measured cause for every other remaining suppression. It does not require zero total suppressions. Therefore these three quality-rejected routes may remain suppressed if release evidence reports each relation, the measured quality failure, candidate count, and confirms zero egress-collision causes. The existing no-crossing test remains mandatory. Any changed route count or lane membership on slide 02 must be attributed; the reported 13-to-10 lane change is attributable to both the 4wd interval correction and expanded generic label ladder and must be remeasured from published-main-derived implementation.

The measured quality failures are not evidence that a third row solves route quality. If a later policy seeks to render these relations, it requires a separate design choice against the declared bend/detour limits and remains outside this correction.

## Ownership and interfaces

Project/Schedule own the corrected dependency lag and derived dates. The frozen baseline and Actual resource remain unchanged. View owns lane-mode selection and required title/delta intent; it gains no coordinate, row-count, or HALCYON-specific override. Layout owns the generic finite candidate ladder, collision checks, lane identity/membership, reserved row extents, diagnostics, and route results. The lane row extent must continue through `required_row_block_extents` with the #480 `text_line_block` input. Group bands include header rows per #481; lane table columns continue through #487 `measure_table_columns`; #486 attached points stay on their host lane under the existing attachment rule. Scene projects completed geometry and route/suppression facts. Adapters serialize those facts without rerouting or inferring causes.

## Version and migration

The WIP v0.26 is occupied by published main (#479/#486). Lane mode therefore uses View v0.27, rebuilt from the current live v0.26 schema, with v0.26 transitioning and all earlier View fields retained. The label-row extension is Layout behavior and adds no View or Theme field. No Scene schema change is intended unless current diagnostic structures cannot represent the cause-specific evidence; if so, return to design before implementation rather than encode causes in adapter text.

The correction changes planned dates and may change schedule-derived output, lane membership, lane heights, canvas dimensions, routes, or diagnostics. It does not change Actual observations, baseline schedule facts, automatic-row output policy, group identity, lane stable identity rules, route quality limits, or the six literal #467 criteria and three #494 criteria.

## Acceptance evidence required

Use current-main-derived code and resources. Rerun the normal scheduler and public materializers for every affected context. Inspect the resulting SVG and Scene batch; report byte changes and visible geometry. Demonstrate 02 at no more than 12 lanes with the named chain, required visible names and deltas, deterministic insertion behavior, zero egress-collision suppressions, cause-specific accounting for every other suppression, and no required-label route crossings on 02/11/12. Attribute every 02 membership change. Validate presets and all selected public slides independently; the in-memory experiment is not acceptance evidence.

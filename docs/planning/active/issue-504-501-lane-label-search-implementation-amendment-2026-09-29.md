# Implementation amendment — R2a lane label search (#504)

This amendment supersedes R2's search/suppression wording in the [R1–R5 plan](issue-504-501-readable-default-implementation-plan-2026-09-29.md) and its [earlier amendment](issue-504-501-layout-background-implementation-amendment-2026-09-29.md). It follows the [design correction](../../design/issue-504-501-lane-label-search-correction-2026-09-29.md) and [architecture review](../../reviews/current/issue-504-501-lane-label-search-architecture-review-2026-09-29.md). Other slices remain unchanged.

R4's completed scale and 2em member-label rule must merge before R2a implementation; this dependency overrides the original numeric slice order.

| R2a work | Acceptance gate |
| --- | --- |
| Share normalized member-label intent and Theme-measured box between preflight/final placement; use completed R4 scale and mark/subtrack obstacles; derive finite stagger demand into per-row minima before `fill`. | Shared content/measurement, interval concurrency, obstacle accounting, scale identity, growth and no membership/scale re-solve. |
| Add lane-only full-band contact search within each actual final row extent. Preserve side order and R4 2em end gap; deterministic ranking; no generic 512 truncation. | Fixed-row finite candidate completeness against a continuous interval oracle; row containment, stable ties, and non-lane output unchanged. No hypothetical-height sweep. |
| Add typed `SurfacePlacement` suppression facts: lane/member, final row extent, remaining capacity, `capacity` or `obstruction`; extend internal profile resolution with exact required source IDs still short. | `capacity` only when `fill` leaves no available row block and the allocator names the short timeline source; `obstruction` for a final-row geometric miss. Every fact matches one suppressed text and aggregate count. |
| Batch materialize 02/11/12 with intended context-specific profiles; inspect Scene/SVG and byte-compare 04/07/15. | Report shown/suppressed names and attribution. If 02 still suppresses after full-band search, stop R2 and publish a further design correction before claiming #504 complete. |

No full local test suite is required by this amendment; use focused tests/materializers, then CI for the release gate. Do not publish generated acceptance evidence before the stop gate passes.

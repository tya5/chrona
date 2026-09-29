# Implementation amendment — #504/#501 R2/R3

Amends the [R1–R5 plan](issue-504-501-readable-default-implementation-plan-2026-09-29.md) after the [design correction](../../design/issue-504-501-layout-background-correction-2026-09-29.md) and [architecture review](../../reviews/current/issue-504-501-layout-background-correction-architecture-review-2026-09-29.md). R1 and R4/R5 are unchanged. Publish this amendment before resuming paused R2/R3 product edits.

| Slice | Added owner/work | Focused and public gate |
| --- | --- | --- |
| R2 | Layout preflight receives closed font metrics and derives interval-overlap label levels; row requirements and lane-only `place_label` tangent extent consume legal block space. Extend typed suppression decisions with lane extent, useful extent and reason. | Synthetic stagger lane, 02/11/12 actual resources, suppression attribution, non-lane label invariance; inspect Scene/SVG and materializer byte diffs. A 02 `fill`-only diagnostic changed 14 suppressions to two, but is not accepted evidence. |
| R3 | In `surface_composer.py`, narrow `_validate_background_shapes` to permit only later-painted `calendarClosed` over row/group/header band; preserve all other overlap errors. Complete bundled and HALCYON Theme paint. | Positive starter Scene/SVG/raster and legend parity; negative same-order, same-role and unrelated translucent overlap tests; regenerate affected public evidence in a batch. |

If measured demand or background layering still exposes a new contract gap, stop that slice and publish another design correction. Do not replace the validator with an unconditional bypass or hide missing names behind a revised warning count.

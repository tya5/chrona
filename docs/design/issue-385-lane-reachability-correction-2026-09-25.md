# Design Correction: Historical lane helper reachability (#385)

**Decision:** Accepted.

## Evidence and decision

`presentation.layout.lanes` was introduced during the package split and is
not imported by product code.  Its only consumers are its unit tests.  Its
date-based `LaneItem`/stacking model is not an input to current surface
composition: the live Layout owns resolved visual placement through
`surface_composer` and `surface_quality`, where a lane is a physical text
plane rather than a mark-stack allocation policy.

Deletion is therefore the correct result.  Integrating the helper would add a
second, unsupported placement policy; staging it would preserve dead product
code; and adding a synthetic import would falsify reachability.

## Architecture alignment review

| Boundary | Finding | Decision |
| --- | --- | --- |
| Layout composition | `surface_composer` is the sole live producer of completed placement. | Preserve it unchanged. |
| Surface quality | `surface_quality` owns collision-space lanes for completed text. | Preserve it unchanged. |
| Historical helper | `lanes.py` has no product caller and models a different, date-stack abstraction. | Delete it with its tests. |
| Public Scene/rendering | Neither imports nor serializes the helper. | No artifact or contract change. |

This is a removal of an abandoned parallel implementation, not a new
lane-layout feature.  No compatibility shim is retained because there is no
supported public API or live internal caller to preserve.

## Acceptance

* `lanes.py` and tests that solely specify it are absent.
* Module reachability passes without a staged exemption.
* Focused live Layout tests, full pytest, and conformance remain green.

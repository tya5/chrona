# Mark composition implementation review (#398, #396, #397, #399)

## Scope reviewed

The implementation migrates the live Theme, View, and Actual Set contracts to
v0.8, v0.14, and v0.3; introduces completed role-relative mark geometry; and
publishes Scene v0.3 paint, clip, and endpoint fields. It intentionally does
not retain the previous live contract versions as a compatibility ingress.

## Architecture result

* Theme owns lane-relative height, offset, paint order, and corner treatment.
* Layout owns base-lane allocation, mark bounds, nested icon bounds, open-actual
  placement, progress containment, and all label collision decisions.
* Scene carries only completed geometry and validates cross-primitive clip
  references.
* SVG projects validated data into a paint layer and source-ordered linked
  interaction layer. It does not choose geometry, infer a host, or measure
  text.

The annotation-number collision discovered during public materialization was
resolved by placing note indexes through the same completed Layout label solver
as variance labels, rather than by weakening the overlap invariant.

## Evidence

* Focused contract/layout/Scene/SVG/materializer batch: **24 materializer
  checks**, **95 integration and focused checks**, and **35 Scene/SVG checks**
  passed during this slice.
* All 21 declared corpus slides were regenerated through the public
  materializer. The generated Scene documents now use v0.3 and reflect the
  intentional role geometry, icon badge, open actual, and clipping treatment.
* Vocabulary reachability reports 10 schema ingress values; corpus coverage
  completes without an error.

## Remaining release gate

The full suite and CI remain the final release gate before closing the four
issues. No design or boundary exception is outstanding.

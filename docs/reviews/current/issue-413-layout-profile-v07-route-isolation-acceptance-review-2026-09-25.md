# Issue #413 I413-1 — Layout Profile v0.7 Route Isolation Acceptance Review

**Status:** accepted; #413 remains open for I413-2 annotation presentation.
**Implementation:** `4b157f95`
**CI:** [run 36121877414](https://github.com/tya5/chrona/actions/runs/36121877414)

## Accepted boundary

`chrona/layout-profile/v0.7` is the sole live Layout Profile contract.  It
requires `reviewSurface.annotationRouting`, carries that policy in the Layout
manifest, and applies it only to completed annotation-leader geometry.
Dependency routing continues to consume only `relationRouting`.

| Requirement | Evidence | Result |
| --- | --- | --- |
| Closed v0.7 contract | The v0.7 schema requires finite `maxBends` and `maxDetourRatio`; the v0.6 schema and runtime dispatch were removed. | Pass |
| No compatibility reader | resource parsing, Layout validation, closure loading, package inventory, and public corpus accept only v0.7. | Pass |
| Independent policy propagation | `LayoutManifest` serializes distinct relation and annotation policies; focused tests prove an annotation policy change leaves relation values unchanged. | Pass |
| Correct Layout ownership | Layout quality-checks annotation routes against annotation policy; Scene receives only completed placements. | Pass |
| Atomic public migration | all 21 public materializations and coverage evidence were regenerated; only declared Layout provenance changed, not SVG drawing bytes. | Pass |

## Verification

* focused Layout, annotation geometry, contract, closure, schema-vocabulary, and
  packaged-resource tests: 86 passed;
* public materialization of all 21 corpus slides, conformance, checked coverage
  and realization reports, diagnostic inventory, semantic reachability, and
  structural checks passed;
* CI run 36121877414 passed on Ubuntu, macOS, and Windows, including parallel
  pytest, conformance, checked generators, wheel build, and installed-wheel
  smoke.

## Architecture review

The Profile declares only finite quality limits.  Layout selects and validates
the leader route.  Scene and adapters neither read policy nor reconstruct a
route.  The independent Manifest fields prevent annotation tuning from
silently changing dependency routing and preserve the Project/View -> Layout
-> Scene -> adapter authority chain.

## Remaining disposition

I413-2 will replace the generic annotation semantic fallback with typed,
purpose-specific box, text, leader, and explanatory-arrow terminal placements.
That work is intentionally not included in this migration slice.

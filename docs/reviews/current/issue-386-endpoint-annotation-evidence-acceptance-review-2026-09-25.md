# Acceptance Review: Endpoint Annotation Evidence (#386)

**Decision:** Accepted.

## Delivered evidence

- `controller-z/annotations` is a declared public corpus slide with a View
  v0.13 containing two `explanatory-arrow` annotations.
- `firmware-slip` binds the actual `finish` endpoint; `bringup-risk` binds the
  planned `finish` endpoint.
- `annotations-review` reserves an explicit full-width required rail, and its
  Context declares the measured 1600×1100 surface required by the existing
  eight-row review allocation.
- Layout selects the `rail` rung for explanatory arrows under the View fallback
  ladder, places both boxes, and computes both completed orthogonal leaders.
  The second leader has five bends, providing committed obstacle-avoidance
  evidence rather than a router-only assertion.
- Scene and SVG carry `annotation-box`, `annotation`, and `annotation-leader`
  provenance.  Neither Scene nor adapter imports the Layout router.

## Boundary review

Project annotations remain semantic notes and were not changed.  The View
owns audience-specific explanatory intent; Layout owns allocation, text
measurement, boxes, ports, fallback selection, and routes; Scene projects
completed placements; SVG serializes them.  Theme remains appearance-only.

The two feasibility corrections were necessary and accepted: an optional
content-sized slot is not evidence of capacity; a side rail competes with the
table/timeline minimum widths; a below-row rail requires an explicit Context
viewport; and explanatory arrows must use the same declared rail policy as
callouts.  Each correction was designed and published before its implementation.

## Verification

- Focused public materializer integration: **23 passed**.
- All declared corpus materializers, including the 20th new slide: passed.
- Conformance and generated vocabulary/diagnostic checks: passed.
- Three-platform conformance CI, parallel pytest, wheel budget, and installed
  wheel smoke: passed on [run 36026398856](https://github.com/tya5/chrona/actions/runs/36026398856).

## Handoff

#375 owns measuring the new annotation purpose/anchor evidence.  #384 remains
the owner of marker geometry; this feature did not extend that vocabulary.

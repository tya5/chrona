# Issue 278 Automatic Point Fold Acceptance Review

## Decision

Accepted.  The complete automatic-point policy is published on `main` through
`da3952e` and `b006466`.  This review records the final implementation and
architecture gate; it introduces no additional behavior.

## Delivered behavior

- `rows.points` is legal only for automatic rows and defaults to `own-row`.
- `predecessor` folds only a point with one selected span predecessor; all
  ineligible cases retain a normal row.
- `group-header` requires both `grouping.presentation: header` and a visible
  plot title.  It produces a typed header-targeted projection rather than an
  empty table row.
- Layout derives deterministic header tracks from `GroupPlacement` capacity,
  creates completed point marks, required title labels, ports, routes, and
  annotation anchors, and retains planned, actual, and scenario facets on the
  same stable folded identity.
- Scene only projects those completed placements.  No fold target, text
  measurement, label placement, or route is calculated in Scene.
- HALCYON's TVAC-slip view opts in with a representative header fold; its
  regenerated SVG removes the Pre-ship-review table row while retaining the
  header marker, title, and dependency endpoint.

## Architecture review

| Boundary | Verified responsibility | Excluded responsibility |
| --- | --- | --- |
| Project / Scheduler | schedule and relation facts | View policy and geometry |
| View / projection | automatic policy, typed header target, stable comparison members | coordinates and text metrics |
| Layout | header capacity/tracks, marks, labels, ports, routes, annotation anchors | renderer syntax and raw Project traversal |
| Scene | semantic projection of completed placements | geometry or policy fallback |
| Renderer | serialization of Scene primitives | semantic interpretation |

The header is never represented as a fake review row.  Point table cells are
therefore absent by construction, while relation and annotation consumers use
the same completed mark identity.  Invalid header configurations diagnose at
the typed View boundary rather than silently falling back to `own-row`.

## Verification evidence

- Focused projection, Layout/Scene, and materializer tests pass.
- Public materializer verification covers every example manifest context.
- Full local suite: `398 passed, 7 skipped`.
- Pull request #319 conformance passed on `ubuntu-latest` and `macos-latest`,
  including import-direction/reachability checks, tests, wheel build, and
  installed-wheel smoke tests.
- The regenerated 1920×1080 HALCYON TVAC-slip SVG was rasterized and reviewed:
  the group-header title, folded diamond/title, and dependency path are
  visible; no blank point table row or clipping was found.

## Disposition

Issue #278 is ready to close.  The follow-on quality work for alternate
automatic policies remains separate from this accepted implementation.

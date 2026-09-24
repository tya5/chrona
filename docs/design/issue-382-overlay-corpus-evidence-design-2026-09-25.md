# Design: Overlay corpus evidence (#382)

**Decision:** Accepted.

## Use case

Add one HALCYON programme-board corpus slide, `overlay-briefing`, that presents
the existing programme through a composition whose main review surface and
detail rail are independently positioned within an `overlay` root.  It proves
the current Layout v0.4 grammar in a materializable user-facing surface; it is
not a migration of PR #272's old dossier or a new presentation feature.

The new Context reuses the current HALCYON project, View, Theme, Color Scheme,
actual set, and detail profile.  It has a new live v0.4 Layout Profile and a
current v0.15 Context.  Reuse is deliberate: the variable under evidence is
the Layout composition, not stale subject data or legacy appearance assets.

## Composition and ownership

The root overlay has three non-raw Layout facts:

1. a block guide positions the main table/timeline review region below the
   title;
2. an inline barrier is derived from the main review member(s), and a detail
   rail anchors from its end with a Theme-token gap; and
3. a second anchored child uses the guide/parent axes to establish deterministic
   title and timeline-axis alignment.

All slots remain existing semantic sources.  Layout Profile resolution owns
reference scope, dependency ordering, guide fractions, barrier extrema, anchor
offsets, and safety checks.  Surface composition receives resulting slot bounds
as it does for every current profile; Scene carries completed placements only.
No View, Scene, renderer, or coverage-tool policy is added.

## Evidence model

The manifest declares both SVG and Scene artifacts.  They are generated only
by the public materializer.  A focused test resolves the exact new resource
with the current Theme and measurements, then asserts the decided slot bounds:
the anchored detail rail begins after the derived barrier plus its token gap,
and the guide-targeted region has the specified guide coordinate.  This proves
the solver behavior that a serialized Scene alone intentionally does not
encode.  The Scene artifact proves the same Context reaches user-visible
materialization and its slots/primitives remain valid.

The regenerated presentation coverage report proves the declared `overlay`,
`guides`, `anchor`, and `barriers` paths now have corpus evidence.  It remains a
non-gating curation report; it does not become an independent validator.

## Gallery disposition

`programme-at-scale` remains deferred.  One fixed viewport overlay is evidence
of the grammar, but not a responsive View/Layout pair or a reusable gallery
comparison.  Its blocker will say this explicitly rather than imply that the
absence of overlay evidence is its only problem.

## Architecture alignment

| Boundary | Responsibility |
| --- | --- |
| Corpus Context | Declares immutable inputs and output evidence. |
| Layout Profile / engine | Resolves guide, barrier, and anchor geometry. |
| Surface Layout | Uses resolved slot bounds to compose review geometry. |
| Scene / renderer | Projects completed placements; no constraint solving. |
| Coverage / gallery | Reads and links published evidence only. |

This preserves the established Context → View → Layout → Scene → materializer
direction and avoids both a second layout grammar and raw-coordinate escape
hatches.

## Acceptance

* The new slide materializes byte-identically through the public materializer
  and supplies v0.2 Scene evidence.
* Its current Layout resource declares and solver-tests overlay, guide, anchor,
  and barrier behavior.
* Coverage shows those declarations as covered; gallery deferred wording is
  accurate; no obsolete #272 resource is imported.

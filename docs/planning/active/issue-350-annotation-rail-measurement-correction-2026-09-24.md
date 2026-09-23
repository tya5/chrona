# Design Correction: Measured Annotation Rail Allocation (#350)

**Status:** Design complete — supersedes the unimplemented rail allocation portion of the annotation-rail correction.

## Finding

The initial rail proposal exposed an `annotations` slot but the current source
measurement supplied the literal placeholder `"annotations"`.  A footer flow
therefore allocated a 180 by 19.6 region, independently of the visible View
callout text and its requested icon advances.  Layout then correctly rejected
the completed callout as unplaceable.  Enlarging a fixture or adding an
adapter-side fallback would conceal the broken composition boundary.

## Corrected contract

Before the Layout Profile is solved, the render use case constructs a typed
annotation measurement input from the selected visible View annotations.  For
each callout it carries its text typography, wrapping intent, and the exact
leading/trailing advances resolved from the same typed visual requests and
closed icon assets that Layout later composes.  The `annotations` source
measurement derives its required inline and block extent from those runs.  No
coordinate, route, or candidate choice enters this input.

Layout then solves the declared rail against the real required extent.  During
composition it uses the same measured visual advances to build the annotation
box and `note-index`; Scene receives only the completed result.  The rail is
optional only when the selected View has no visible annotations.

## Architecture consistency review

This restores the established measurement chain: View selects annotation
facts; Context closes requested assets; Theme provides typography/ratios;
Layout owns both source measurement and geometry; Scene projects; adapters
serialize.  It eliminates the placeholder's independent sizing policy and
does not give the use case any placement or routing authority.

## Implementation plan

1. Introduce a renderer-neutral typed annotation source-measurement value and
   build it after typed visual requests/assets are closed but before Layout
   solving.
2. Make `measure_sources` derive the `annotations` measurement from those
   runs, including visual advance and wrapped line height.
3. Add the Controller Z optional footer rail only after the measured source is
   available; exercise annotation, numbered note index, icon, box, and leader
   in one integration fixture.
4. Characterize absent-annotation generated output as byte-stable and prove
   that Layout, not Scene, retains all text measurement and routing imports.

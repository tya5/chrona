# Design Correction: Complete Annotation Visual Composition (#350)

**Status:** Design complete — refines the implementation boundary in the measured annotation rail correction.

## Finding

The annotation rail correction correctly moved callout text measurement ahead
of Layout solving, but its implementation plan did not close every selected
text target through candidate composition. `annotation` and `note-index` are
independent View targets: the former consumes rail extent, while the latter is
anchored beside the selected mark. Sending the note index through generic text
composition after its coordinate was chosen leaves no visual advance to
reserve. It is therefore a target-inventory and ownership gap, not an overflow
case to hide by shortening content.

## Corrected contract

Layout exposes one pure visual-advance resolver. It translates a closed typed
View request plus closed icon asset and typography role into leading/trailing
advance. Both pre-solve annotation source measurement and final candidate
placement call that resolver.

Layout completes both targets before Scene projection:

- `annotation-text:<id>` reserves its resolved advances within the measured
  annotation rail, then emits its text and visual placements.
- `note-index:<id>` reserves its own resolved advances at its mark anchor,
  then emits its text and visual placements.

The Controller Z rail is an independent optional root-level slot. It must not
be a footer-flow item, because a flow's panel allocation is not a rail-width
policy and can shrink a required callout below its measured extent. A selected
annotation therefore changes only the explicitly declared rail region.

Themes that materialize these semantic targets bind `annotation-text.fill` and
`note-index.fill` explicitly. This preserves the existing paint boundary:
Layout chooses neither color nor paint role; Scene receives semantic primitive
roles and resolves their already-declared Theme bindings.

## Architecture consistency review

The correction preserves the successor pipeline without introducing an adapter
exception: View selects targets, Context closes assets, Theme supplies
typography/ratios and role bindings, Layout measures and composes all geometry,
Scene projects completed placements, and renderers serialize them. In
particular, the render use case passes semantic source facts into Layout but
does not calculate coordinates, routing, wrapping, or icon geometry.

## Implementation and acceptance plan

1. Extract and unit-test the shared Layout visual-advance resolver; use it for
   existing candidate labels and annotation source measurement.
2. Add the independent Controller Z annotation slot and explicit standard-theme
   bindings for both annotation text targets.
3. Complete `note-index` visual placement in the annotation Layout branch and
   exclude both completed targets from generic text composition.
4. Add an integration fixture with numbered annotation, annotation visual,
   note-index visual, box, and leader; prove both visual bounds precede their
   text bounds.
5. Run focused, full, public materializer, and generated-SVG-diff gates. Any
   absent-annotation output change must be explained by the explicitly
   declared layout-profile evolution, not accepted as incidental churn.

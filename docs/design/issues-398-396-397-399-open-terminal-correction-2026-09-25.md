# Open actual terminal correction (#399)

## Trigger

The mark-composition implementation carries `endTreatment: open` through
Layout and Scene, but v0.5 SVG currently serializes an open actual as the same
closed `rect` used for a finished actual.  The field is therefore inspection
metadata, not a completed visual treatment.  It fails #399's requirement that
the as-of edge cannot be mistaken for a finish.  The implementation also
limits a progress clip host to `Rect`, contradicting the preceding Scene
correction, which permits a completed open host outline.

## Corrected decision

An open actual is a Layout-owned **open-span outline**, not a renderer
interpretation of a rectangle.  Layout emits a closed, filled polygon with a
right-facing continuation chevron and rounded leading corners where the
role's resolved corner radius permits them.  Its pointed terminal has no
closed vertical edge, so it communicates continuation rather than completion.
The polygon remains a completed host extent from the observed start through
the actual-set as-of coordinate.

`MarkPlacement.mark_shape: open-span` and its completed path commands are the
single representation of that decision.  Scene projects it as a `Symbol`
primitive retaining `endTreatment: open`; SVG serializes the completed symbol
outline without choosing coordinates, a chevron size, or rounding.  A closed
span remains a `Rect`.

## Clipping consequence

The progress fill remains a rectangle, with a square trailing edge.  A clip
reference may name either a completed `Rect` host or a completed `Symbol` host
with a closed outline.  SVG serializes the corresponding completed host shape
inside `clipPath`.  It does not recreate host geometry.  This lets the
in-flight actual host its own progress fill while keeping the open terminal
and leading containment exact.

## Invariants

* Only Layout selects `open-span`; a Scene builder neither infers it from
  dates nor changes a closed mark.
* An `open-span` has non-empty, closed completed path commands contained in
  its bounds; its ports still identify the observed start and as-of end.
* `endTreatment: open` requires `open-span`, and `open-span` requires
  `endTreatment: open`.
* A clip host is a preceding, same-slot completed `Rect` or `Symbol`; a
  `Symbol` host must carry its own outline.  Open and closed hosts use the
  same reference rule.
* Source order and `paintOrder` remain unchanged; the additional outline does
  not introduce a renderer-owned mark or a new accessibility item.

## Architecture review

Temporal facts stay in Actual Set, View still selects the comparison, Theme
still supplies paint and corner treatment, and Layout alone chooses and
measures the terminal geometry.  Scene is the typed completed geometry
boundary.  SVG merely selects the already-declared primitive form when
serializing a clip or graphic.  This restores the Specification 32/50
boundary and makes the open-as-of policy observable in every Scene consumer.

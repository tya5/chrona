# Issue 279: Rounded Path Geometry Design Correction

## Trigger

During I279-A implementation, passing a Theme radius through
`RelationPlacement` and `ScenePrimitive` was found insufficient.  It would
leave the renderer to decide how an orthogonal corner is rounded and would not
enforce the design's per-turn radius clamp.  That contradicts the completed
Layout-to-Scene geometry boundary.

## Corrected handoff

Layout will introduce a closed, renderer-neutral `PathCommand` vocabulary:
`move`, `line`, and `quadratic` commands, each with finite coordinates.  Given
an orthogonal route and a requested radius, Layout shortens each adjoining leg
by `min(requested_radius, preceding_leg / 2, following_leg / 2)`, then emits a
quadratic turn with the original vertex as control point.  Zero radius emits
the existing move/line sequence byte-for-byte.  The command sequence starts
at the source port, ends at the target port, and never asks Scene or a renderer
to infer a bend, a radius, or a control point.

A positive point radius follows the same principle: Layout supplies a closed
rounded-diamond PathCommand sequence inside the completed mark bounds.  A
zero-radius point remains the existing Symbol primitive.  Span marks remain
rectangles with a Layout-clamped radius.

`RelationPlacement` and `ShapePlacement` carry path commands where applicable;
`ScenePrimitive` receives them verbatim.  The renderer adapters serialize that
vocabulary directly.  Their only allowed target-specific choice is syntax,
not geometry.  Unsupported syntax must diagnose rather than substitute a
square or mitred shape.

## Architecture review

This correction strengthens the existing ownership model.  Theme supplies a
metric, View supplies no geometry, Layout closes all geometric decisions, Scene
projects typed values, and renderers serialize them.  It does not introduce a
renderer-shaped persisted resource or permit Scene to route or round paths.

## Implementation consequence

The I279-A prototype is not published.  It will be rebuilt after this document
is merged, with command construction and invariants tested before any renderer
or example Theme opt-in is added.

# Issue 277 Axis-Band Projection Correction

## Trigger

The first implementation attempt made Layout produce coarse interval rectangles but
left Scene unable to emit them. Existing `axisBand` is a text semantic and existing
Theme vocabulary supplies only `axis-major` and `axis-minor` stroke roles. Letting
Scene silently drop the rectangle, or reinterpreting it as a text label, violates the
completed-placement projection boundary.

## Corrected boundary

Layout owns a typed `axis-band` rectangle and its measured, centred optional label.
Scene must project both placements verbatim. The semantic registry gains a distinct
axis-band decoration semantic whose Theme role is explicitly declared by the resolved
Theme contract; it must not borrow a grid or text role. Theme packages provide the
required band fill/stroke token binding as part of the same atomic rollout.

Grid paths remain separate typed placements: coarse boundaries use `axis-major`, fine
boundaries use `axis-minor`, and every path begins at the timeline plot top. Scene
selects semantic roles from Layout placement identity only; it does not infer levels,
coordinates, fitting, or band geometry.

## Consequences

The #277 implementation must update the semantic registry, all supported public Theme
packages, Scene projection tests, and regenerated public SVG evidence together. A
partial change that emits rectangles without Theme support, or computes rectangles
without emitting them, is not acceptable.

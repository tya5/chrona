# #349 I349-2 Completed Gradient Geometry Review

**Decision:** accepted.

`LinearGradient` no longer exposes an adapter-interpreted angle. Scene consumes
the completed primitive/canvas bounds and Theme-selected clockwise-inline angle,
then stores finite Layout-plane start/end coordinates. SVG emits those exact
coordinates through `userSpaceOnUse`; a differently sized primitive receives a
different endpoint pair with the same visible direction.

The SVG adapter neither reads Theme/Scheme nor computes gradient geometry. The
public Elevated fixture was regenerated only through the materializer, and its
three group bands now contain separate completed gradient definitions. Focused
Scene and renderer checks passed (`39 passed`).

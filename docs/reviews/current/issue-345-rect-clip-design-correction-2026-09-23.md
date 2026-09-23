# #345 Rectangular Clip Design Correction

**Decision:** defer `clip.rect` from the initial `chrona-output/visual/v0.6`
profile.

Implementation review found that current Chrona has no Layout-owned grouping or
containment placement which can supply a clip rectangle.  A Theme cannot own
that geometry, and allowing Scene to infer it from a primitive, viewport, or
slot would make Scene choose layout geometry.  Reusing text-overflow policy is
also incorrect: it is content feasibility, not visual composition.

The initial profile therefore ships the independently complete treatments for
which the existing ownership chain is closed: linear gradient, single
drop-shadow, and line cap/join.  This is not an SVG omission or fallback.
Rectangular clipping remains explicitly deferred until a future design adds a
typed Layout containment/group placement, its semantic owner, and cross-target
fidelity evidence.  The correction preserves the Layout → Scene → adapter
direction and avoids a renderer-shaped pseudo-layout API.

# Architecture Review — Completed Background Placements (#389, #409)

**Decision:** Accept.

One ShapePlacement path for row, group, header, and calendar backgrounds
removes Scene's remaining geometry inference and gives Layout the only place
where completed overlap can be validated. The no-overlapping-translucent-fill
invariant is stricter and clearer than ordering alpha layers; an outline is a
separate visual treatment rather than a renderer blend workaround.

Acceptance requires cross-slot row/group bounds, alternating selection,
background overlap rejection, calendar-outline acceptance, direct Scene
projection, stable adapter order, public corpus evidence, and full tests.

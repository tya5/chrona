# Architecture Review — Axis Tier Role and Label Contract (#405, #406, #407, #408, #400)

**Result:** Accepted.

The correction preserves the required ownership chain: View declares finite
presentation intent; Layout selects intervals, measures and records outcomes;
Scene receives completed placements; Theme and adapters paint them.  Splitting
one multi-role declaration into single-role tiers avoids coupling band, grid,
and label placement in either Layout or Scene.

Unit-specific forms belong at the View boundary, before locale-aware formatting
and measurement.  The `auto` candidate map is finite, explicit, and still
owned by View; Layout makes the deterministic fit decision without reading
legacy fields or inventing a format.  Fiscal origin remains Project-calendar
data under the separately accepted Project v0.7 correction.

No cross-layer responsibility moves, no compatibility ingress is retained, and
the correction leaves the later failure-policy design intact.

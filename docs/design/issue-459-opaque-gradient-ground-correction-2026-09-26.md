# Design Correction — Opaque Linear-Gradient Ground (#459)

The #459 corpus probe found that `controller-z/generated/elevated.scene.json`
places classified marks over a completed opaque `group-band` Rect whose paint
contains an absolute-coordinate linear gradient. The initial #459 design
treated every gradient host as unsupported, but the Scene contains all values
needed to determine its interior colour at the policy sample point. Rejecting
the published slide would be an avoidable design gap. No #459 product code has
been published; this correction precedes implementation.

## Selected ground rule

An earlier Rect remains a ground candidate if its `opacity` is 1 and it has
either a flat hex fill or a completed opaque linear gradient with absolute
start/end coordinates and finite ordered hex colour stops. At the primitive's
painted sample point, project onto the start→end vector, clamp to `[0, 1]`,
interpolate between adjacent stops in sRGB channel space, and round each
channel deterministically to the nearest byte. The sampled colour becomes
the `groundColor` used by the same shared contrast kernel; the finding also
records `groundKind: gradient-sample` (or `flat`, `canvas`). A zero-length
gradient vector resolves to the final stop, matching the deterministic
renderer-neutral convention selected here. A shadow does not replace an
opaque interior fill at the sample point.

Unknown paint types, incomplete stops, non-opaque host paint and unsupported
geometry remain explicit diagnostics. The policy is not a raster oracle: the
batch SVG inspection must verify a representative elevated mark against the
adapter's actual gradient output. A gradient can vary across a wide mark;
the centre/painted-edge sample is the finite #459 policy, not a promise that
every pixel meets the floor.

## Whole-architecture review and plan amendment

Theme remains the authoring authority for gradient stops, Layout/Scene carry
completed geometry, the pure Scene paint-analysis kernel derives one sample,
and the SVG adapter continues serializing the same completed gradient. This
uses no renderer-private fallback and does not read a Theme in the policy.
The #459 implementation plan adds gradient interpolation fixtures and elevated
SVG inspection to its first and second slices. The prior initial design's
gradient-exclusion sentence is superseded only for this exact opaque linear
form. Published base: `8f07e532`.

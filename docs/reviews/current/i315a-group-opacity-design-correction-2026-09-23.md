# I315-A Design Correction: Distinct Group-Decoration Opacity Roles

## Trigger

Implementation inspection found that `groupBand` and `groupHeaderBand` both
project to the `group-band` Scene visual role, while the existing completed
Scene gives their rectangles different alpha values (`0.12` and `0.20`).  A
single Theme role cannot represent both values without restoring a
Scene-side literal or a renderer-side exception.

## Corrected design

`groupBand` continues to project to the `group-band` visual role.
`groupHeaderBand` projects to a new, distinct `group-header-band` visual role.
Both roles have independent `fill` and `opacity` bindings in Theme.  The
semantic registry is the sole translation point; Layout continues to emit
only geometric group and header placements.

Scene reads each primitive's visual role and copies its resolved opacity.  It
does not select a numeric alpha.  SVG, Typst, and TikZ serialize that completed
primitive alpha.  A renderer that cannot represent a non-default alpha must
reject it with a stable adapter diagnostic rather than discard it.

The public themes preserve the existing visual policy by declaring the
following values explicitly:

| Role | Opacity |
| --- | --- |
| `group-band` | `0.12` |
| `group-header-band` | `0.20` |
| `calendar-closed` | `0.12` |

All other roles may resolve an explicit opacity of `1`; a missing opacity is
not a renderer default or a Scene literal.  Resolved Theme validation rejects
non-finite values and values outside `[0, 1]`.

## Architecture review

This correction retains the established boundaries: Theme owns visual policy,
the semantic registry maps semantic identities to visual roles, Scene copies
already resolved values, and adapters serialize completed primitives.  It
avoids merging two semantic decorations merely because they share a current
fill, preserving a future ability to vary either role without structural
conditionals.

## Implementation amendment

I315-A must first split the registry role and add explicit public Theme
bindings.  It then adds typed opacity access, Scene projection, adapter
delivery, and byte characterization.  The original deferred scope remains
unchanged: stroke-width, mixed fill/stroke, and dash vocabulary are not added
by this correction.

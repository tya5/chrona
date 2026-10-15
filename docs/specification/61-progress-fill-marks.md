# Progress Fill Marks

**Status:** Accepted
**Depends on:** [05 Project Format](05-project-format.md), [06 View Model](06-view-model.md), [08 Scene and Rendering](08-scene-and-rendering.md), [50 Constraint-driven Gantt Surface Quality](50-constraint-driven-gantt-surface-quality.md), [60 Declared Colour Scales](60-declared-colour-scales.md)
**Owns:** a declared display-only progress submark inside one completed host mark.

## 1. Contract

A View may enable one progress submark with a closed declaration:

```yaml
progressFill: {source: actual}
```

The source is exactly one of `actual` or `planned`.  `actual` reads the
selected latest Actual observation's `progress`; `planned` reads the selected
Project object's `plannedProgress`.  Both are fractions in `[0, 1]`.  Progress
is display-only: it neither derives dates nor changes scheduling, Actual
authority, criticality, row order, scale, or mark identity.

The overlay host is the corresponding completed mark: an `actual` source uses
the actual mark, while `planned` uses the planned mark.  An absent source,
absent host, or zero fraction produces no submark.  A fraction of one is a
full-host submark; no alternative fill, estimate, or interpolation is inferred.

When the matching Plan or Actual legend key is declared, it repeats a full
progress inset using the same progress-fill treatment. The other host's key
does not gain a progress inset; no separate legend entry is inferred.

## 2. Layout and Scene boundary

Layout receives the selected fraction and completed host mark bounds. It creates
one renderer-neutral `progress-fill:<host-id>` submark whose inline extent is the
original host extent multiplied by the fraction and whose block bounds equal the
host's. For a native Rect host this remains a Rect; for a host whose Scene identity
is split across painted glyph parts, Layout completes a Symbol contour by
intersecting the fraction region with the nonzero-winding union of the host's
filled parts. A stroke-only point glyph has no fillable interior and produces no
progress submark. Layout owns rounding, clipping, and zero-width omission. The
submark is optional and never displaces text, changes collision policy, or causes
a label fallback.

Every progress placement carries its typed logical `host_placement_id`, independent
of `clip_host_id`. A native rectangle may retain a clip-host relation; a glyph
progress contour is already clipped by Layout and has no Scene clip host. Explicit
window clipping intersects the original fraction region with the visible completed
host; it never rescales the fraction to the shortened visible extent.

Scene projects that completed placement under the closed `progressFill`
semantic binding.  Theme resolves its paint independently from the host and
Scheme.  Scene does not calculate a fraction or geometry; an adapter receives
only the completed primitive and paint.

## 3. Accessibility and relation to other mark work

The submark carries its host object source reference and a stable semantic
purpose, so consumers can identify its declared source without relying on
colour.  The present Scene primitive contract has no per-mark accessible text
payload; it therefore does not duplicate the percentage as an adapter-local
description.  A consumer that needs the numeric value combines the source
reference with the declared Project or Actual fraction.  Introducing an
accessible percentage text requires a versioned Scene metadata contract and is
outside this display-mark slice.  The submark does not own inside label
contrast: inside-label eligibility remains the host-mark contract.  It does
not use a colour scale or conditional-role rule; #314's scale and the progress
semantic are separate axes.

## 4. Non-goals

## Progress track inset (#430)

The `progress-fill` Theme role may declare `progressInset`, a number token
`0 <= r < 0.5`, and `markCornerRadius`, a ratio `0-0.5` of the fill's
smaller side. Both are absent by default. The host mark is the track. Layout
deflates it by `r x host block size` on the block axis and by
`min(r x host block size, host inline size / 4)` on the inline axis. The fill
is that inner track's inline origin plus `inner width x fraction`: 0 draws
nothing and 1 fills the inner track edge to edge at every bar length. With
`r = 0` this is the full-height fill. The completed radius is carried on the
fill Rect; the clip to the host is kept.

This does not add a state/disposition rule engine, gradients, arbitrary nested
bar layers, progress-based scheduling, progress aggregation, or a target-local
draw callback.  #310 already supplies inside labels and #314 supplies declared
object-field colour; those scopes are not reopened.

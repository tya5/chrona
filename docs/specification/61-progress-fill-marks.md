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

## 2. Layout and Scene boundary

Layout receives the selected fraction and completed host mark bounds.  It
creates one renderer-neutral `progress-fill:<host-id>` Rect whose inline extent
is the host extent multiplied by the fraction and whose block bounds equal the
host's.  It owns rounding, clipping, and zero-width omission.  The progress
submark is optional and never displaces text, changes collision policy, or
causes a label fallback.

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

This does not add a state/disposition rule engine, gradients, arbitrary nested
bar layers, progress-based scheduling, progress aggregation, or a target-local
draw callback.  #310 already supplies inside labels and #314 supplies declared
object-field colour; those scopes are not reopened.

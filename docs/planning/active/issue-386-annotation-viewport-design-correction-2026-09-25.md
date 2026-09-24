# Design Correction: Annotation Evidence Viewport (#386)

**Status:** Accepted correction to #386 rail feasibility.

## Trigger

At 1600×900, the full-width 180px annotation rail leaves 508px for the
eight-row timeline, while the declared row policy requires 636px.  The Layout
diagnostic correctly reports the minimum feasible block extent as 1028px.

## Corrected decision

The annotation evidence Context declares a **1600×1100** viewport.  Viewport is
already explicit Context execution evidence, so this is an honest surface
choice rather than a hidden Layout exception.  The executive control remains
1600×900; it answers a different no-annotation review use case.

The annotation Context differs from the control in View, Layout, and viewport
only.  Project, Actual, Theme, Scheme, target, font closure, and all immutable
resource identities remain the same.

## Required verification

- The declared 1600×1100 annotation Context materializes byte-identically.
- Reducing that Context to 1600×900 continues to fail with the actionable
  required-extent diagnostic; the additional surface height is not accidental.
- The control Context and its committed SVG remain unchanged.

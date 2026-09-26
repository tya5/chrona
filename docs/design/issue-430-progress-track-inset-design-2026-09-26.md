# Design — Progress Track Inset (#430)

**Status:** proposed for whole-architecture review. **Plan:** [design plan](../planning/active/issue-430-progress-track-inset-design-plan-2026-09-26.md). **Authorities:** Specification 61, Theme v0.11 role properties.

## Contract

**Theme (v0.11, additive optional role properties, as earlier v0.11 features did).**

The `progress-fill` role may declare:
- `progressInset`: a number token, `0 ≤ r < 0.5`. It is the ratio of the host mark's block size that separates the fill from the track on every side. It is absent or 0 by default.
- `markCornerRadius`: an existing property name, with the same meaning as on marks. It is the ratio `0–0.5` of the fill's smaller side, used as its own corner radius. It is absent or 0 by default.

A value out of range is `E_THEME_TOKEN_TYPE` at the role pointer.

**Layout** (`progress_fill_bounds(host, fraction, inset_ratio)`):
- block inset `b = r × host.blockSize`;
- inline inset `i = min(b, host.inlineSize / 4)`. On a bar shorter than `8b`, the capped inline inset keeps at least half of the host as the inner track, so a short bar still shows its fraction;
- inner track = the host deflated by `i` inline and `b` block;
- fill = `Rect(inner.inline, inner.block, inner.inlineSize × fraction, inner.blockSize)`.

Fraction 0 returns no fill, and fraction 1 fills the inner track exactly, at every length. With `r = 0` the formula reduces to today's arithmetic, `Rect(host.inline, host.block, host.inlineSize × fraction, host.blockSize)`, and the eight committed slides are byte-identical.

The fill radius is `markCornerRadius × min(fill width, fill height)`, completed in Layout like mark radii. `ShapePlacement` gains a `corner_radius` field, 0 by default.

**Scene / adapters.** The progress-fill `ScenePrimitive` receives the completed `corner_radius`; the SVG adapter already serializes `rx`/`ry` for Rects. The clip to the host is kept (#397). With a non-zero inset it is a no-op, and with zero inset it still does its job.

## Example

- `examples/controller-z/themes/progress-track.yaml`: v0.12, extending `executive-light` and replacing the `progress-fill` role with an inset of 0.2 and a radius of 0.5.
- A new `progress-track` slide in the Controller Z manifest renders its three progress fills, which have different bar lengths.
- It is a new materializer (22 in total). The other 21 are unchanged.

## Out of scope

Progress text labels and track styling beyond the host mark's own paint (the host is the track).

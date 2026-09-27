# Design Plan — Progress Track Inset (#430)

**Public base:** `62e389f0` on `main`. **Source of truth:** [Issue #430](https://github.com/tya5/chrona/issues/430), Specification 61 (progress fill marks), the #397 clip fix, Theme v0.11/v0.12.

## Published baseline

- `layout/surface_composer.py::progress_fill_bounds` returns the host mark's full block extent from its inline origin. The width is `host width × fraction`.
- The fill is clipped to its host (#397), so a rounded host gives the fill one rounded end and one square end.
- Nothing is declarable, so an inset capsule inside a track is unreachable.
- Eight committed slides render one or more progress fills. All are default (no inset).

## Literal acceptance ledger

1. “A theme can declare a progress track's padding, and a bar renders as a track with a visibly inset fill with rounded ends of its own.”
2. “With a non-zero padding, a fraction of 1 fills the inner track edge to edge and a fraction of 0 renders nothing, at every bar length.”
3. “With the default padding of zero, the eight committed examples that render a progress fill reproduce byte-identically.”
4. “One committed example renders the inset treatment at more than one bar length, so the short-bar case is in the corpus rather than argued about.”

## Decisions

- The unit of the padding.
- The fraction base (the inner width).
- The fill's own corner radius.
- Short bars, where the inset would consume the inner track.
- The committed example: a derived Theme on Controller Z, so the eight existing slides stay byte-identical.

## Slices

- **I430-1:** Theme property, Layout geometry, Scene radius, the new example, tests.
- **I430-2:** acceptance review.

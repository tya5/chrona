# Design Plan — Colour Scale Separability (#421)

**Public base:** `1e7c2882` on `main`. **Source of truth:** [Issue #421](https://github.com/tya5/chrona/issues/421), Specification 60 (declared colour scales), Specification 34 (Color Scheme suitability), the #400/#449 "never silent, never refused" principle.

## Published baseline

- `model/color_scale.py::resolve_color_scale` maps each View domain value to its Scheme category colour by a dictionary read. Nothing compares the resolved colours with each other.
- Measured with CIEDE2000 on the committed schemes:
  - `control-room-dark` resolves `bus`/`launch` and `payload`/`ops` to identical colours (ΔE00 = 0), and `02-programme-board` ships them.
  - `mission-light` has the same two duplicates; `01-mission-brief` encodes `owner` with it. Its closest distinct pair is 7.6.
  - ORION's `revision` scale is at least 35.
  - `print-mono`'s greys are 2.3–4.7, but no View applies a colour scale with that scheme.
- Scheme `suitability.colorVision` claims (`deuteranopia`, `protanopia`, `tritanopia`, or `none-claimed`) are validated but never used by a check.

## Literal acceptance ledger

1. “No colour scale resolves two domain values to the same colour.”
2. “A scale whose colours are not separable produces a diagnostic naming the colliding values.”
3. “The check honours the scheme's declared colour-vision suitability.”

## Decisions

- **Metric and threshold.** CIEDE2000 with a stated minimum. CVD simulation for claimed deficiencies (Machado 2009, severity 1).
- **Severity and timing.** A warning at scale resolution, before Layout, per #449, surfaced in the CLI and in the Scene diagnostics.
- **Scheme fix** for the two committed collisions.
- **Gate.** A test that no committed Scene carries the warning.

## Slices

- **I421-1:** the checker, the warning transport, the scheme fixes, tests and evidence.
- **I421-2:** literal acceptance review.

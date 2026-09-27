# #467 B1b-2 Stroke Footprint: Miter Envelope Amendment

**Status:** Design correction to the [stroke-aware footprint design](issue-467-l3b-b1b-2-stroke-aware-footprint-correction-2026-09-27.md), based on public baseline `074bd55590961376c557dac9356a2121e047909a`.

## Decision

Replace the prior path-control-point expansion of `2 × stroke_width` per side and its miter-limit-four assumption with a conservative, target-independent expansion of `10 × stroke_width` per side. The bound is intentionally loose. Do not change ScenePaint, adapter output, cap/join policy, or assign target-specific lane widths. Layout still derives geometry-only extents from the resolved Theme/icon metrics; ScenePaintResolver remains the sole paint conversion. No new paint policy is introduced.

This bound reflects admitted output behavior: TikZ emits general paths with no explicit miter override and inherits TikZ's default miter limit 10; PDF output uses the pinned svglib/ReportLab path and its effective limit 10; SVG and its PNG derivative use the SVG default 4. Typst currently rejects these general paths. A target-independent envelope avoids making Layout depend on which adapter will later serialize the Scene. See [TikZ path actions](https://tikz.dev/tikz-actions), [SVG stroke-miterlimit](https://www.w3.org/TR/fill-stroke-3/#StrokeMiterlimitProperty), [Adobe PDF Reference](https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/pdfreference1.7old.pdf), and pinned dependencies `svglib==2.2.0` / `reportlab==5.0.1` in `pyproject.toml`.

Rectangles remain expanded by half stroke width; centerline segments retain the single `ObstacleSegment.stroke_width` carrier; only control-point path envelopes use the 10× expansion. Never expand the same stroke both in coordinates and in a stroke-width carrier. Collision clearance remains separate. If an adapter's admitted effective limit changes above ten, return to design; do not silently adjust adapter or Layout paint behavior.

## Gate and migration

The 02 ≤12 feasibility criterion remains a strict later hard gate, along with all issue acceptance checks. Re-run it with the new envelope and current data. If it fails, stop and return to design; do not weaken ≤12 or substitute target-specific lane allocation. This is a documented geometry-bound migration, not an output migration: expected lane collision/placement changes are possible, but Scene paint and serialized rendering are unchanged. The normative rules are updated in [Specification 38](../specification/38-review-row-composition.md) and [Specification 46](../specification/46-completed-scene-paint.md).

Unchanged ownership and path-closure requirements remain as specified by the predecessor correction, including symbol/glyph/icon geometry migration into Layout, point legend swatches, preserved primitive/part order and IDs, glyph contain-center behavior, paint:none omission, icon cap/join/stroke scaling, and no post-resolution Scene paint mutation. This amendment changes only the conservative path-stroke envelope.

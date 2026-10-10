<!-- chrona:literal-acceptance/v1 -->

# Issue #1287 — point glyph outline acceptance

Published preparation: `d4215dcca0138de90329829caa44f7497bd8b14d`, ordinarily
adopting #1283's pending PR head `8ba462d826e1fc18a47070350a844a84c0ade8b1`
and ready main `484f5cd83ac24e91b7d435be18dfb5be1ebade04`.
This is a preparation checkpoint, not a merged dependency or release base.
[Selected design and architecture review](https://github.com/tya5/chrona/issues/1287#issuecomment-6088427990).
Local acceptance is verified; public artifact and release gates remain pending. Do not close.

## Literal issue acceptance

### Issue #1287

- Source: [Issue #1287](https://github.com/tya5/chrona/issues/1287)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | With `stroke` and `strokeWidth` bound, the completed gate `Symbol` carries a stroke paint of that width on its filled contour, and the legend swatch for the same role carries the identical paint. | met | [Scene/SVG integration tests](../../../tests/integration/test_point_glyph_role_outline.py): inline/catalogue × lane/automatic point and legend share paint; inside/center/outside clips; catalogue intrinsic width, round cap/join and original local geometry retained. [Contour tests](../../../tests/unit/chrona/presentation/layout/test_filled_contour.py): nonzero union, overlap, holes, quadratics and deterministic order. | — |
| 2 | The mark contrast gate judges the stroke against the ground when the fill is below the floor (the primitive's own edge), Scene-checkable. | met | [Contrast integration cases](../../../tests/integration/test_point_glyph_role_outline.py): the original fill fails the floor without the contour; the added stroke wins against an external ground and reaches 3:1. SVG assertions identify that exact primitive. | — |
| 3 | Absent stroke binding is byte-identical. Synthetic fixture test. | met | [Byte/refusal integration cases](../../../tests/integration/test_point_glyph_role_outline.py) compare complete serialized Scene and actual SVG bytes to independently frozen pre-#1287 Scene projection from `8ba462d8`, with no added Layout contour. The same inputs cover lane/automatic × inline/catalogue × absent/stroke-only/outline-pattern (12 cases), without normalization. Width-without-ink retains its existing refusal. | — |
| 4 | Do not edit `examples/**`; the reviewer adopts it in slide 25. | met | [Published scope](https://github.com/tya5/chrona/issues/1287#issuecomment-6088427990) excludes authored examples and generated evidence. Adoption remains reviewer-owned. | — |

## Programme-level criteria (optional)

Current prepared-parent integration/outline/projection batch: 39 passed (31.67s),
including the independent frozen projection comparisons.
Earlier focused batch: 281 passed (29.93s); expanded integration batch: 11 passed (16.49s), including complete-Scene/SVG byte checks and catalogue finish preservation.
[Lane footprint/port test](../../../tests/unit/chrona/presentation/layout/test_point_outline.py) retains the completed gate width rather than planned-role fallback and keeps semantic ports on the original part. [Projection test](../../../tests/unit/chrona/presentation/scene/test_mark_geometry.py) separates intrinsic catalogue finish metadata from a role-bound outline.

## Architecture conclusion

Layout completes union geometry, widths, footprints and clips; Scene resolves role ink and ordinary finish, forwarding catalogue width/cap/join only as an intrinsic tuple. Source parts and local geometry remain intact; an opted-in contour can enlarge the visible footprint and change downstream allocation/translation under existing rules. No Scene grammar or renderer geometry decision is added. Built-ins, stroke-only glyphs, outline-pattern ghosts and non-point consumers retain their existing treatment. Independent read-only review found no concrete ownership defect.

Required release evidence: adoption of the current ready main after earlier M0 slices, fresh before/after public artifact counts and inspection, exact-head PR checks, automatic derived sync and successful three-OS pytest/conformance/wheel on the exact published main containing this review.

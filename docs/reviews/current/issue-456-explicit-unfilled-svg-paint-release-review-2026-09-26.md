<!-- chrona:literal-acceptance/v1 -->

# Release Review — Explicit Unfilled SVG Paint (#456)

## Literal issue acceptance

### Issue #456

- Source: [Issue #456](https://github.com/tya5/chrona/issues/456)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | No shape in any committed SVG lacks a `fill` attribute, except inside `<clipPath>`. | met | [SVG checker](../../../tools/check_svg_explicit_fill.py); [renderer test](../../../tests/unit/chrona/presentation/renderers/test_v05_svg.py) | — |
| 2 | Closed days on every committed slide render as their theme declares, and no slide shows black stripes. | met | [HALCYON SVG](../../../examples/halcyon-1/generated/01-mission-brief.svg); [all-slide contrast report](../../diagnostics/presentation-contrast.md) | — |
| 3 | The print theme's outline milestones render hollow. | met | [print SVG](../../../examples/halcyon-1/generated/03-launch-campaign.svg); [SVG checker](../../../tools/check_svg_explicit_fill.py) | — |

## Programme-level criteria (optional)

All 21 committed SVGs pass the explicit-fill gate. All 844 closed-day shapes
now have `fill="none"` and an explicit stroke; the print slide has 12
outline-only planned marks, including four path marks. The adapter fix added
856 `fill="none"` attributes to regenerated public SVGs without any other
element changes. Raster inspection of the HALCYON hero and print slide showed
no black closed-day bars and hollow outline milestones. The chosen closed-day
policy remains an outline hairline, not an opaque stripe; the report's
composited Scene floor remains at least 1.10:1.
The [5b909ce8 CI matrix](https://github.com/tya5/chrona/actions/runs/36207540414)
passed all three OS jobs and newest-Python public reproduction.

## Architecture conclusion

Scene owns the completed absence of fill. The SVG adapter serializes that
absence explicitly, including when a pattern override is present; it does
not invent a visibility policy. The shared SVG path also covers PNG. The
checker guards the public adapter contract on every committed SVG.

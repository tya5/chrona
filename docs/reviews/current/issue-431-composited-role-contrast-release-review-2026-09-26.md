<!-- chrona:literal-acceptance/v1 -->

# Release Review — Composited Role Contrast and Corpus Visibility (#431)

## Literal issue acceptance

### Issue #431

- Source: [Issue #431](https://github.com/tya5/chrona/issues/431)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A decoration role whose composited contrast against its ground falls below the declared floor is diagnosed, or is explicitly declared absent. | met | [policy](../../../src/chrona/presentation/scene/contrast_policy.py); [focused test](../../../tests/unit/chrona/presentation/scene/test_contrast_policy.py) | — |
| 2 | No committed slide ships a background decoration below the floor. | met | `tools/presentation_contrast.py --check`; generated [contrast report](../../diagnostics/presentation-contrast.md) | — |
| 3 | The per-purpose contrast table is generated from committed Scenes and checked. | met | [contrast report](../../diagnostics/presentation-contrast.md); `presentation-contrast` conformance entry | — |
| 4 | One committed slide shows each of the five decorations visibly: alternating rows, axis bands, closed days, group bands and group header bands. | met | [executive Scene](../../../examples/controller-z/generated/executive.scene.json); report witness section | — |
| 5 | A scheme or theme that binds a text-painting state role below its floor is rejected, with a diagnostic naming the role. | met | [closure test](../../../tests/unit/chrona/presentation/test_color_scheme.py) | — |
| 6 | No committed slide draws state-coloured text below its floor. | met | [contrast report](../../diagnostics/presentation-contrast.md) state-text rows and `--check` | — |

## Programme-level criteria (optional)

The checked report has no policy errors and names three five-decoration
witness Scenes; generated materializer evidence is the release artefact.

## Architecture conclusion

Theme closure owns authoring rejection.  View selects independent row and
group decoration families, Layout places them, Scene transports completed
paint/absence/treatment facts, and the report observes only those facts.  The
adapter receives no contrast decision.  The release is acceptable once the
public materializer and multi-platform CI evidence for this exact commit are
green.

## Adapter-output re-review after #456

The original review inspected completed Scene paint. #456 exposed that an
unfilled SVG shape used SVG's implicit black fill, so Scene-only contrast
evidence was insufficient for closed-day stripes. The adapter now emits
`fill="none"`; the [all-SVG gate](../../../tools/check_svg_explicit_fill.py)
passes 21 committed slides. XML inspection found all 844 closed-day shapes
explicitly unfilled and stroked. The [HALCYON hero](../../../examples/halcyon-1/generated/01-mission-brief.svg)
and [print slide](../../../examples/halcyon-1/generated/03-launch-campaign.svg)
were raster-inspected without black bars; print outline marks are hollow.
The [contrast report](../../diagnostics/presentation-contrast.md) still has
zero errors and a minimum decoration ratio above 1.10:1. Thus the five
decoration witnesses and state-text floor are now checked against actual
adapter output as well as Scene intent. The
[5b909ce8 CI matrix](https://github.com/tya5/chrona/actions/runs/36207540414)
passed across Ubuntu, macOS, Windows and newest-Python reproduction. The
final review commit CI remains the release gate.

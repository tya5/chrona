# Gantt Comparison Release Gate — I58-5 Acceptance Review

**Release candidate:** `08cee9c110d499911edc35008a64ff629ad946a3`

## Acceptance matrix

| Requirement | Evidence | Result |
| --- | --- | --- |
| A58-01 | Scene structural test rejects direct measurement/routing imports; I58-1 acceptance review | Pass |
| A58-02…A58-06 | Layout, ingress, Scene, table/label/relation/group/legend unit coverage | Pass |
| A58-07 | `.venv/bin/python -m pytest -q` | 251 passed |
| A58-08 | Controller-Z, ASTER overview, and all three HALCYON public materializer byte checks | Pass |
| A58-09 | CairoSVG rasterization and visual inspection at 1600×900, 1920×1080, and 1200×1120 declared HALCYON viewports | Pass |

## Visual findings

Mission brief retains measured plot labels without clipping. Programme board has
visible contiguous group headers plus complete Planned/Actual/Milestone legend
pairs. Launch campaign retains labels and accepted dependencies without a
fallback route or text clipping. No renderer-specific correction was applied.

## Architecture and release disposition

The reviewed public path remains Project → View/Detail/Layout Profile/Theme →
Layout placements → Scene projection → SVG/PNG. Layout owns table allocation,
text measurement, label selection, route acceptance, group capacity, and legend
geometry. Scene has no corresponding fallback computation. The seven warnings
are pre-existing `jsonschema.RefResolver` deprecations, not test failures or
surface diagnostics. Issue #58 is ready to close after this review is merged.

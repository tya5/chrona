<!-- chrona:literal-acceptance/v1 -->

# #1515: Graphical variance legend swatches

## Literal issue acceptance

### Issue #1515

- Source: [Issue #1515](https://github.com/tya5/chrona/issues/1515)
- Observed: 2026-10-15

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | a legend swatch for the variance roles (a filled rect in the role's bound colour) that does not require a text contrast treatment. | met | [Synthetic technical-print SVG](../../../tests/integration/test_variance_legend_swatch.py): three declared variance entries, correct bound fills, no text treatment, strict contrast policy; no Actual data needed. [Classification and floor tests](../../../tests/unit/chrona/presentation/scene/test_variance_legend_contrast.py) retain Text treatment and distinguish 3.0 mark from 4.5 required text. | — |

## Programme-level criteria (optional)

## Architecture and release

[Published design, architecture review and implementation plan](https://github.com/tya5/chrona/issues/1515#issuecomment-6186493843).
Implementation: [018aa48f4](https://github.com/tya5/chrona/commit/018aa48f41ef218cedf4147066b72859e5512481).
Specs46 §8 and49 define the finite role/kind/purpose classification. Theme
state-text declarations remain valid; Layout geometry, role-bound paint,
adapters, schemas and finding/report shapes are unchanged. Independent review
found no blocking issue. Diagnostic codes retain mark policy attribution.

Focused new/registry/SVG checks: 45 passed. Final Scene/contrast/legend/Actual/
documentation regression run: 1143 passed. CI artifact
comparison and exact review-containing main three-OS release remain required
before closure; the literal row alone does not authorize closing the issue.

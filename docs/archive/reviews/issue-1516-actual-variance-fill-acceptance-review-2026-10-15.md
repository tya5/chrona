<!-- chrona:literal-acceptance/v1 -->

# #1516: Actual variance fills

## Literal issue acceptance

### Issue #1516

- Source: [Issue #1516](https://github.com/tya5/chrona/issues/1516)
- Observed: 2026-10-15

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | a way for a Theme to bind the actual mark's colour per variance class (for example `actual-behind` selected by the same classification that selects `variance-behind`). | met | [Public SVG regressions](../../../tests/integration/test_actual_variance_paint.py) exercise finite classes and technical-print's red overdue Actual; [model selection](../../../tests/unit/chrona/presentation/model/test_actual_variance_selection.py) covers absent/unclassified/source/folded facts; [paint precedence](../../../tests/unit/chrona/presentation/scene/test_actual_variance_fill_resolution.py) preserves fixed glyph/ink and bypasses replaced gradients. | — |

## Programme-level criteria (optional)

## Architecture and release

[Published design/implementation plan and architecture review](https://github.com/tya5/chrona/issues/1516#issuecomment-6186265536),
[normative contract](../../specification/07-style-and-theme.md#actual-variance-fill-selection-1516).
Style/review normalization selects completed fill from existing variance facts.
Scene only consumes the object-keyed result on `actual` primitives; Layout's
geometry, stroke/clip/hosting ownership and semantic/contrast identity remain
unchanged. Fill traits admit no geometry/effect properties. Internal zero variance
uses the existing canonical `variance-on-track`, with no compatibility alias.
Independent review found no blocking ownership or paint-precedence issue.
Implementation: [2f988adef](https://github.com/tya5/chrona/commit/2f988adef).
Specs61/46 keep progress overlays independently painted and contrast-tested.
The dedicated overlay regression preserves its primitives and reports genuine
new progress/host contrast warnings; positive host-fill fixtures do not mask
the host with an optional overlay.

Final focused Scene/Scheme/contrast, model, SVG, hosting, axis and documentation
run: 1152 passed. Final PR CI [run 38698146372](https://github.com/tya5/chrona/actions/runs/38698146372)
completed successfully. Immutable artifact review [11954233482](https://github.com/tya5/chrona/pull/1539#issuecomment-6186818437)
found 109 before/after files with no additions or retirements; all 100 public
SVG/Scene files were byte-identical, with only inventory source positions differing.
The exact review-containing main release on `0c20e7802c4d64594fbc77d3a1dcbc5afb78809e`
completed successfully: [run 38699780693](https://github.com/tya5/chrona/actions/runs/38699780693),
including the three-OS full matrix, conformance, wheel/doc smoke, newest-Python
materializer and MCP-floor checks. Issue #1516 was closed after this evidence.

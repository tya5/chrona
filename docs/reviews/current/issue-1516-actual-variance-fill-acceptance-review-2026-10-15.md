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

Focused model/review tests: 122 passed; combined paint/model/hosting: 96 passed;
Scene/Scheme/contrast regressions: 1047 passed; new selection/paint/SVG tests:
13 passed in one collection (unique test filenames).
Final combined Scene/Scheme/contrast, model, SVG, hosting, axis and documentation
run: 1152 passed; documentation/literal review checks passed again after archiving
released records. CI/public-materializer artifact review and the exact
review-containing main three-OS release are required before issue closure.

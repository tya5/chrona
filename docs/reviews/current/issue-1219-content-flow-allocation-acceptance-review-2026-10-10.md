<!-- chrona:literal-acceptance/v1 -->

# Acceptance review — content-sized Flow block allocation (#1219)

Baseline: PR1277 completed direct Flow children only. Current completion:
`d799cb46`, following pre-code specification `4ddc6c78` and
[selected plan/architecture review](https://github.com/tya5/chrona/issues/1219#issuecomment-6138977120).
The existing native natural-block owner now closes container descendants at
their effective inline extents; Flow resolves child inline declarations before
the shared line selection. Fixed/capped hosts retain truthful overflow.
Spec33 section13.1 is normative. This does not solve #1214's failed-probe bound.

## Literal issue acceptance

### Issue #1219

- Source: [Issue #1219](https://github.com/tya5/chrona/issues/1219)
- Observed: 2026-10-13

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic finite content-sized Flow: known inline width causes two lines, allocated block encloses both line heights plus gap; no spurious track overflow. | met | [`test_content_flow_block_allocation.py`](../../../tests/unit/chrona/presentation/layout/test_content_flow_block_allocation.py) `test_a_known_inline_width_that_wraps_two_lines_allocates_both_lines_without_a_track_overflow` (allocated 60 = 20 + 40, children on separate lines, no warning). | — |
| 2 | Synthetic one-line, nested/container, min/max and genuinely insufficient declared host cases retain intended allocation and honest overflow. | met | [Completion fixtures](../../../tests/unit/chrona/presentation/layout/test_flow_completion_closure.py) cover nested columns with gap/padding, row/overlay and native grid-cell widths, declared Flow width, intrinsic/bounded targets and fixed/capped shortage. The existing one-line/fitContent/aspect and source-budget controls also pass. | — |
| 3 | Layout owns geometry; no Scene/adapter measurement or corpus edits. | met | [Implementation](https://github.com/tya5/chrona/commit/d799cb46): Layout engine only; natural measurement and arrangement share width resolution. No Scene, adapter or authored examples changes. | — |
| 4 | Disclose public SVG/Scene/diagnostic effects from one CI snapshot; focused tests and planned release gates pass. | not met | [Plan](https://github.com/tya5/chrona/issues/1219#issuecomment-6138977120): focused198 tests pass, but current-head CI snapshot and containing-review exact-main three-OS release remain required. Earlier PR1277 evidence is not substituted for them. | — |
| 5 | 2026-10-07 comment: a Flow child's declared `inlineSize: fixed` is ignored by `_flow_lines` (it uses `max(itemMinInlineSize, preferred_inline)`); resolve child inline declarations consistently for natural demand and arrangement, with synthetic fixed, minmax and content cases. | met | [Completion fixtures](../../../tests/unit/chrona/presentation/layout/test_flow_completion_closure.py) verify fixed/min-content/max-content/fitContent/minmax/fill/fr/aspect targets, actual wrap coordinates, contradictory fixed ceilings and retained typed source-budget overflow. The shared `_flow_lines` path computes both natural demand and placement. | — |

## Programme-level criteria (optional)

Focused command (198 passed): the completion, intent engine, nested Flow,
Flow block intent, source sizing, table/heading inline budget, cross-size
stretch and flexible-track unit files. All61 earlier direct Flow/cross/aspect
controls passed before the broader run. Grid cells retain their native track
allocation; this change does not introduce child-size-based grid allocation.
The issue stays open for literal row4 and exact-main release acceptance.

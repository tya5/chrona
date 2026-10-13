<!-- chrona:literal-acceptance/v1 -->

# Issue 1394 native Rect patterns

## Literal issue acceptance

### Issue #1394

- Source: [Issue #1394](https://github.com/tya5/chrona/issues/1394)
- Observed: 2026-10-13

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | a Scene with a pattern-filled Rect exports to Typst and TikZ with the pattern drawn (or the declared fallback plus a warning); `chrona export` of `technical-print` succeeds; no change for scenes without patterns. | met | [Selected design/plan](https://github.com/tya5/chrona/issues/1394#issuecomment-6139529828); [projection/byte checks](../../../tests/unit/chrona/presentation/renderers/test_v05_typeset.py), [repeat coverage](../../../tests/unit/chrona/presentation/renderers/test_pattern_repeat.py), [native grammar matrix](../../../tests/integration/test_native_typesetter_patterns.py). [Native CI38357185387](https://github.com/tya5/chrona/actions/runs/38357185387) passes all18 cases including technical-print on both targets, plus6 synthetic cases. Artifact11793805724 was independently checked; both technical-print PDFs were inspected. Exports use the existing documented render --format seam, not a new CLI alias. | — |

## Programme-level criteria (optional)

Native SVG/Typst/TikZ images at0/45/90 degrees were compared as one batch:
tile phase, channels and rounded clips retained. Pattern quadratic segments
use the exact two-control cubic conversion in TikZ. Existing non-pattern
serialization is unchanged by the pattern branch. No fallback or warning
delivery path was introduced; unsupported non-Rect patterns still refuse.

## Architecture conclusion

Layout/Scene own complete tile and region facts. The renderer helper only
enumerates intersecting cells of that supplied affine lattice. Target adapters
serialize them with native host/tile clipping. No schema or corpus edits.
Product authority:d5f6418f; native evidence head:6f2f366a. Verify final current-head
PR checks and exact-main three-OS release containing this acceptance disposition
before deliberate issue closure.

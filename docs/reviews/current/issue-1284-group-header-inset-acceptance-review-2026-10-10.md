<!-- chrona:literal-acceptance/v1 -->

# Issue #1284 — group-header inset acceptance

Source: `058b3e7822d9f0e8a939fb6055e2bc2b39496d3d`, refreshed by an ordinary merge of ready main `0617e671c51ed14fe0d242a37a18a744bd85b7e8`. [Published contract and architecture review](https://github.com/tya5/chrona/issues/1284#issuecomment-6087491029). Layout owns the offset and measured content extent; glyph bounds and Scene projection are unchanged. [PR #1312](https://github.com/tya5/chrona/pull/1312) needs fresh readiness checks: the previous head passed functional checks but failed readiness on its stale main base. Public artifact and release gates remain pending; do not close.

## Literal issue acceptance

### Issue #1284

- Source: [Issue #1284](https://github.com/tya5/chrona/issues/1284)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | With `labelInset: i` the header text's inline start equals the band start plus `i` times the font size, Scene-checkable per group; absent is today's output. | not met | [Synthetic tests](../../../tests/integration/test_group_header_label_inset.py) check both groups, plain/marked Scene and SVG starts, and absent/zero equality. Exact public before/after byte audit remains pending. | — |
| 2 | The measured header width includes the inset, so `groupHeaderBand: text` (if present) encloses it. | met | [Extent tests](../../../tests/integration/test_group_header_label_inset.py) verify plain/marked completed Layout content extents from band start through measured glyph/run ends. Text-sized bands are not present in this slice; #1283 consumes that closure. | — |
| 3 | Synthetic fixture test. | met | [New integration tests](../../../tests/integration/test_group_header_label_inset.py) and capability batch: 14 passed (6.14s). Existing group/tab/Theme regression batch: 248 passed (51.55s). | — |
| 4 | Do not edit `examples/**`; the reviewer adopts it in slide 25. | met | [Source diff](https://github.com/tya5/chrona/compare/7503e53076e4e0b924051b89759a9ece6ca9d038...264f27afdff894899b19c754de500b9f82987c1f) contains only Layout, capability admission, schema description, specification and synthetic tests. | — |

## Programme-level criteria (optional)

None. After the base refresh, the 14 inset/capability tests passed again and S0 passed with 38 schema structures equal (four unchanged baseline-invalid fixtures). Earlier broader evidence: 248 group/tab/Theme tests, 451 mapped documents/739 probes, and Scene delivery ownership (31 dataclasses/225 fields). Required next evidence: exact-head PR artifact/checks, then exact-main three-OS pytest/conformance/wheel with this review published.

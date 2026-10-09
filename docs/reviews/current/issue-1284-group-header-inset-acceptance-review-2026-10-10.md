<!-- chrona:literal-acceptance/v1 -->

# Issue #1284 — group-header inset acceptance

Source PR: [#1312](https://github.com/tya5/chrona/pull/1312), head `5a7fff0bb19f3dbbe0739c5e5da926b183ba77ae`, base `abbe91a40b46621e448eded6dcfb42b1dd97bb7b`. Public contract and design: [Status](https://github.com/tya5/chrona/issues/1284#issuecomment-6087491029). Layout owns the offset and measured text extent; glyph geometry and Scene projection remain unchanged.

PR checks: [run 37998576407](https://github.com/tya5/chrona/actions/runs/37998576407) succeeded, including conformance, all three pytest shards, newest-Python reproduction, MCP floor, and derived readiness. [Artifact audit](https://github.com/tya5/chrona/pull/1312#issuecomment-6090365186): 149 safe paths; all 70 SVGs and 70 Scenes byte-identical to the base; no additions or removals; only the diagnostic inventory changed. Current focused batch: 115 passed; S0: 38 schema structures equal.

## Literal issue acceptance

### Issue #1284

- Source: [Issue #1284](https://github.com/tya5/chrona/issues/1284)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | With `labelInset: i` the header text's inline start equals the band start plus `i` times the font size, Scene-checkable per group; absent is today's output. | met | [Synthetic integration tests at the PR head](https://github.com/tya5/chrona/blob/5a7fff0bb19f3dbbe0739c5e5da926b183ba77ae/tests/integration/test_group_header_label_inset.py) check both groups, plain and marked Scene/SVG positions, and absent/zero equality. The [artifact audit](https://github.com/tya5/chrona/pull/1312#issuecomment-6090365186) confirms all 70 public SVG/Scene outputs remain byte-identical. | — |
| 2 | The measured header width includes the inset, so `groupHeaderBand: text` (if present) encloses it. | met | The same [integration tests at the PR head](https://github.com/tya5/chrona/blob/5a7fff0bb19f3dbbe0739c5e5da926b183ba77ae/tests/integration/test_group_header_label_inset.py) verify the completed Layout content extent from the band start through the inset and shown glyph/run ends; #1283 consumes that extent for the optional text-sized band. | — |
| 3 | Synthetic fixture test. | met | [Integration tests at the PR head](https://github.com/tya5/chrona/blob/5a7fff0bb19f3dbbe0739c5e5da926b183ba77ae/tests/integration/test_group_header_label_inset.py) and the current focused batch: 115 passed. | — |
| 4 | Do not edit `examples/**`; the reviewer adopts it in slide 25. | met | PR diff has no `examples/**` changes. [Board #454, Lanes](https://github.com/tya5/chrona/issues/454) assigns target adoption to the reviewer and states it is not a dev closing condition. | — |

## Programme-level criteria (optional)

None.

## Architecture conclusion

Layout owns the offset and measured content extent. The exact-main release gate for a commit containing this review is still pending; this review does not claim merge or issue closure.

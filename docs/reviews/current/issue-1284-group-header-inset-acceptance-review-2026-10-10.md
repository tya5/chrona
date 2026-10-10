<!-- chrona:literal-acceptance/v1 -->

# Issue #1284 — group-header inset acceptance

Source PR: [#1312](https://github.com/tya5/chrona/pull/1312), head `c82a335935eb80352dbe94277da341bbf5a0783c`, base `e614aae4a8c891546e1863c609d03fac9a707002`. Public contract and design: [Status](https://github.com/tya5/chrona/issues/1284#issuecomment-6087491029). Layout owns the offset and measured text extent; glyph geometry and Scene projection remain unchanged.

PR checks: [run 38006132465](https://github.com/tya5/chrona/actions/runs/38006132465) succeeded, including all pytest shards, newest-Python reproduction, conformance, MCP and derived readiness. [Artifact audit](https://github.com/tya5/chrona/pull/1312#issuecomment-6091376674): 151 safe paths verified against the exact base; all 71 SVGs and 71 Scenes byte-identical; no additions or removals; only the diagnostic inventory changed. Current-base focused batch: 16 passed; S0: 38 schema structures equal. PR #1312 merged as `92fdc4cbefc7a9509328f031a15b4736a4a56394`.

## Literal issue acceptance

### Issue #1284

- Source: [Issue #1284](https://github.com/tya5/chrona/issues/1284)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | With `labelInset: i` the header text's inline start equals the band start plus `i` times the font size, Scene-checkable per group; absent is today's output. | met | [Synthetic integration tests at the PR head](https://github.com/tya5/chrona/blob/c82a335935eb80352dbe94277da341bbf5a0783c/tests/integration/test_group_header_label_inset.py) check both groups, plain and marked Scene/SVG positions, and absent/zero equality. The [artifact audit](https://github.com/tya5/chrona/pull/1312#issuecomment-6091376674) confirms all 71 public SVG/Scene outputs remain byte-identical. | — |
| 2 | The measured header width includes the inset, so `groupHeaderBand: text` (if present) encloses it. | met | The same [integration tests at the PR head](https://github.com/tya5/chrona/blob/c82a335935eb80352dbe94277da341bbf5a0783c/tests/integration/test_group_header_label_inset.py) verify the completed Layout content extent from the band start through the inset and shown glyph/run ends; #1283 consumes that extent for the optional text-sized band. | — |
| 3 | Synthetic fixture test. | met | [Integration tests at the PR head](https://github.com/tya5/chrona/blob/c82a335935eb80352dbe94277da341bbf5a0783c/tests/integration/test_group_header_label_inset.py) and the current-base focused batch: 16 passed. | — |
| 4 | Do not edit `examples/**`; the reviewer adopts it in slide 25. | met | PR diff has no `examples/**` changes. [Board #454, Lanes](https://github.com/tya5/chrona/issues/454) assigns target adoption to the reviewer and states it is not a dev closing condition. | — |

## Programme-level criteria (optional)

None.

## Architecture conclusion

Layout owns the offset and measured content extent. The exact-main release gate for a commit containing this review is still pending; this review does not claim merge or issue closure.

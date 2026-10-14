# Gallery freshness and viewport survey review

<!-- chrona:literal-acceptance/v1 -->

Design, architecture and implementation plan: [living record](https://github.com/tya5/chrona/issues/1474#issuecomment-6158249825).
READY baseline1299e952; G1 commit56fa67d6, canonical survey1d35966c,
annotation fallback0fa35d73. Focused combined suite:37 passed; strengthened
overlap regression:2 passed. Actual viewer-fit600x340 now renders with5 warnings.
Gallery --check passes; three generated pages only refresh referenced-resource
excerpts. No examples or derived-owned reports changed.

## Literal issue acceptance

### Issue #1474

- Source: [issue](https://github.com/tya5/chrona/issues/1474)
- Observed: 2026-10-14

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | Both tools pass on main. | not met | Gallery check passes locally; canonical138-case baseline renders116 with161 warnings and22 failures, eliminating21 snapshot-input omissions while revealing5 additional Layout failures. The annotation failure is fixed and its actual600px case passes. Remaining inline-capacity contract is [awaiting disposition](https://github.com/tya5/chrona/issues/1474#issuecomment-6158879745); no failures hidden or cases retired. PR/main release evidence is still required. | — |
| 2 | Each is either in the CI gate or explicitly documented as manual. | not met | [Conformance registration](../../../conformance/run_conformance.py) gates the gallery in PR/release CI. Final matrix ownership awaits corrected coverage/runtime and the capacity disposition; opt-in --jobs uses isolated processes and deterministic aggregation. | — |
| 3 | Do not edit `examples/**`. | met | [Source diff](https://github.com/tya5/chrona/compare/1299e952a22d855f81d04f32b5ad81ff0f462da8...0fa35d73) changes tools, synthetic tests, Layout fallback propagation and three renderer-owned documentation pages only. [Identity tests](../../../tests/unit/tools/test_check_draft_viewport_matrix.py) preserve authored bytes/snapshot/assets; derivative Contexts are temporary and truthfully pinned. | — |

## Programme-level criteria (optional)

None. Keep issue1474 open; partial slice publication is not full acceptance.

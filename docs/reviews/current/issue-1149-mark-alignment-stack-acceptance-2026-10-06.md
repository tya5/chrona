<!-- chrona:literal-acceptance/v1 -->

# Issue #1149 — acceptance review

Authority: [living design/implementation plan](https://github.com/tya5/chrona/issues/1149#issuecomment-6011834979), Spec07/08/24. Published implementation: [PR #1188](https://github.com/tya5/chrona/pull/1188), head `04bd2340`, source `37af4b82`, verified ready-main `7b8051ca`. Synthetic rows are met; the reviewer [explicitly deferred adoption](https://github.com/tya5/chrona/issues/1149#issuecomment-6016572875) to its migration PR, outside the dev closing gate. Close only after the three-OS release run on the exact main commit publishing this review succeeds; cite that run in the closing comment.

## Literal issue acceptance

### Issue #1149

- Source: [Issue #1149](https://github.com/tya5/chrona/issues/1149)
- Observed: 2026-10-06

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | For any track size, a centred symbol's centre equals the track centre within 0.01 px. | met | [Public Scene synthetic tests](../../../tests/integration/test_mark_alignment_stack.py): 10/16/30px, automatic/lane rows, default and explicit alignment, folded points and explicit offset precedence. | — |
| 2 | With a declared stack, the members' order and gaps are as declared, and the stack is centred. | met | [Completed Layout closure](../../../tests/unit/chrona/presentation/layout/test_mark_band_allocation.py), 10/16/30/100px; [public Scene and actual SVG](../../../tests/integration/test_mark_alignment_stack.py), automatic/lane rows, missing observations, independent point/frame bounds and oversized stacks. | — |
| 3 | Changing one member's height re-centres the stack with no other edit. | met | [Layout and public Scene height-change assertions](../../../tests/integration/test_mark_alignment_stack.py); [closure invariants](../../../tests/unit/chrona/presentation/layout/test_mark_band_allocation.py). | — |
| 4 | Absent declarations give byte-identical output. | met | [Synthetic explicit-offset/ignored-align identity](../../../tests/integration/test_mark_alignment_stack.py); [final snapshot11412541419](https://github.com/tya5/chrona/actions/runs/37459748130), head04bd2340/basecd1bbdde:139 baseline Git blobs independently verified, all65 SVG+65 Scene byte-identical, unchanged paths/no retirements. All139 ready-main7b8051ca outputs independently match the snapshot; only diagnostic inventory and presentation coverage reports change. | — |
| 5 | Target B migrates to `align` and a stack. | deferred | [Reviewer-approved disposition](https://github.com/tya5/chrona/issues/1149#issuecomment-6016572875): adoption is the reviewer's step, not a dev closing condition; no claim that migration already happened. | [Reviewer-owned migration tracking](https://github.com/tya5/chrona/issues/1149#issuecomment-6016572875); its post-review supplies the migration PR. |

## Programme-level criteria (optional)

No additional programme criteria.

## Verification and architecture

Focused Layout/symbol/radius/stroke batch: 89 passed; public Scene/SVG integration: 18 passed. Theme/schema/reference/capability: 157 passed; diagnostics: 26 passed (overlapping scope, not additive). Python3.11 follow-up: 100 vocabulary/float-guard/schema/allocation/presentation tests passed; after following #1187, 68 allocation/presentation/Scene/SVG/derived-size/source tests passed. Schema equivalence: 523 documents/739 probes, four existing invalid fixtures unchanged; 21 merged #1148 deltas retired. Annotation/reference, literal-review, float-accumulation, diagnostic actionability and Scene ownership gates passed. Old-head CI findings were corrected with stable geometry_sum, float search bounds and a shared logicalAlignment vocabulary; no test exception or frozen definition was changed.

[Final-head PR CI](https://github.com/tya5/chrona/actions/runs/37459748130) passed all three pytest shards, conformance, MCP, newest-Python reproduction and derived-ready. [Serialized sync](https://github.com/tya5/chrona/actions/runs/37462464927) and [exact-SHA derived gate](https://github.com/tya5/chrona/actions/runs/37463305915) succeeded before publishing ready-main `7b8051ca`. The closing comment must verify the full three-OS gate containing this updated review, not substitute the implementation-PR checks.

Theme owns declarations; immutable Layout allocation completes span/symbol bounds, ordered slots, span-only frames, outer extents and warnings. Natural row requirements, ordinary/folded marks and provisional/final lane footprints consume that rule. Scene/adapters perform no new placement; lane membership, dates and paint roles are unchanged. Spec24 connects stack reservation to #1187's merged nominal-track derivation; no dev-A edits to `sources.py`, reviewer YAML or generated artifacts.

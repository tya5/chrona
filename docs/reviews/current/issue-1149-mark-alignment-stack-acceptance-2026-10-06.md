<!-- chrona:literal-acceptance/v1 -->

# Issue #1149 — candidate acceptance

Authority: [living design/implementation plan](https://github.com/tya5/chrona/issues/1149#issuecomment-6011834979), Spec07/08/24. Product: `a1e92ed3`; ready base: `cd1bbdde`. Not release-accepted: final PR/public-materializer evidence, reviewer-owned Target B adoption, and exact-final-main three-OS release remain required.

## Literal issue acceptance

### Issue #1149

- Source: [Issue #1149](https://github.com/tya5/chrona/issues/1149)
- Observed: 2026-10-06

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | For any track size, a centred symbol's centre equals the track centre within 0.01 px. | met | [Public Scene synthetic tests](../../../tests/integration/test_mark_alignment_stack.py): 10/16/30px, automatic/lane rows, default and explicit alignment, folded points and explicit offset precedence. | — |
| 2 | With a declared stack, the members' order and gaps are as declared, and the stack is centred. | met | [Completed Layout closure](../../../tests/unit/chrona/presentation/layout/test_mark_band_allocation.py), 10/16/30/100px; [public Scene and actual SVG](../../../tests/integration/test_mark_alignment_stack.py), automatic/lane rows, missing observations, independent point/frame bounds and oversized stacks. | — |
| 3 | Changing one member's height re-centres the stack with no other edit. | met | [Layout and public Scene height-change assertions](../../../tests/integration/test_mark_alignment_stack.py); [closure invariants](../../../tests/unit/chrona/presentation/layout/test_mark_band_allocation.py). | — |
| 4 | Absent declarations give byte-identical output. | not met | [Synthetic explicit-offset/ignored-align identity](../../../tests/integration/test_mark_alignment_stack.py) passes. Earlier [snapshot11409709933](https://github.com/tya5/chrona/actions/runs/37456006426) at59fcbe33/base61d1fb74 verified139 baseline Git blobs and all65 SVG+65 Scene byte-identical; final-head/new-base corpus comparison remains required. | — |
| 5 | Target B migrates to `align` and a stack. | not met | [Current work record](https://github.com/tya5/chrona/issues/1149#issuecomment-6011834979): reviewer-owned YAML adoption and rendered acceptance are not yet published. | — |

## Programme-level criteria (optional)

No additional programme criteria.

## Verification and architecture

Focused Layout/symbol/radius/stroke batch: 89 passed; public Scene/SVG integration: 18 passed. Theme/schema/reference/capability: 157 passed; diagnostics: 26 passed (overlapping scope, not additive). Python3.11 follow-up: 100 vocabulary/float-guard/schema/allocation/presentation tests passed; after following #1187, 68 allocation/presentation/Scene/SVG/derived-size/source tests passed. Schema equivalence: 523 documents/739 probes, four existing invalid fixtures unchanged; 21 merged #1148 deltas retired. Annotation/reference, literal-review, float-accumulation, diagnostic actionability and Scene ownership gates passed. Old-head CI findings were corrected with stable geometry_sum, float search bounds and a shared logicalAlignment vocabulary; no test exception or frozen definition was changed.

Theme owns declarations; immutable Layout allocation completes span/symbol bounds, ordered slots, span-only frames, outer extents and warnings. Natural row requirements, ordinary/folded marks and provisional/final lane footprints consume that rule. Scene/adapters perform no new placement; lane membership, dates and paint roles are unchanged. Spec24 connects stack reservation to #1187's merged nominal-track derivation; no dev-A edits to `sources.py`, reviewer YAML or generated artifacts.

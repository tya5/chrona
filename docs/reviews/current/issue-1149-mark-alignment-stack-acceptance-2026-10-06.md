<!-- chrona:literal-acceptance/v1 -->

# Issue #1149 — candidate acceptance

Authority: [living design/implementation plan](https://github.com/tya5/chrona/issues/1149#issuecomment-6011834979), Spec07/08. Product: `188ec99a`; ready base: `61d1fb74`. Not release-accepted: final PR/public-materializer evidence, reviewer-owned Target B adoption, and exact-final-main three-OS release remain required.

## Literal issue acceptance

### Issue #1149

- Source: [Issue #1149](https://github.com/tya5/chrona/issues/1149)
- Observed: 2026-10-06

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | For any track size, a centred symbol's centre equals the track centre within 0.01 px. | met | [Public Scene synthetic tests](../../../tests/integration/test_mark_alignment_stack.py): 10/16/30px, automatic/lane rows, default and explicit alignment, folded points and explicit offset precedence. | — |
| 2 | With a declared stack, the members' order and gaps are as declared, and the stack is centred. | met | [Completed Layout closure](../../../tests/unit/chrona/presentation/layout/test_mark_band_allocation.py), 10/16/30/100px; [public Scene and actual SVG](../../../tests/integration/test_mark_alignment_stack.py), automatic/lane rows, missing observations, independent point/frame bounds and oversized stacks. | — |
| 3 | Changing one member's height re-centres the stack with no other edit. | met | [Layout and public Scene height-change assertions](../../../tests/integration/test_mark_alignment_stack.py); [closure invariants](../../../tests/unit/chrona/presentation/layout/test_mark_band_allocation.py). | — |
| 4 | Absent declarations give byte-identical output. | not met | [Synthetic explicit-offset/ignored-align Scene surface and SVG identity](../../../tests/integration/test_mark_alignment_stack.py) pass; complete public corpus byte comparison awaits the final PR snapshot. | — |
| 5 | Target B migrates to `align` and a stack. | not met | [Current work record](https://github.com/tya5/chrona/issues/1149#issuecomment-6011834979): reviewer-owned YAML adoption and rendered acceptance are not yet published. | — |

## Programme-level criteria (optional)

No additional programme criteria.

## Verification and architecture

Focused Layout/symbol/radius/stroke batch: 89 passed; new public Scene/SVG integration file: 18 passed. Theme/schema/reference/capability batch: 157 passed; diagnostic batch: 26 passed (overlapping scope, not additive). Schema equivalence: 523 documents/739 probes, four existing invalid fixtures unchanged; 21 merged #1148 expected deltas mechanically retired. Schema annotations/references, diagnostic actionability and Scene primitive ownership gates passed.

Theme owns declarations; immutable Layout allocation completes span/symbol bounds, ordered slots, span-only frames, outer extents and warnings. Natural row requirements, ordinary/folded marks and provisional/final lane footprints consume that rule. Scene/adapters perform no new placement; lane membership, dates and paint roles are unchanged. Spec24's shared row/track paragraph follows dev-B PR #1187 after its merge; no edits to `sources.py`, reviewer YAML or generated artifacts.

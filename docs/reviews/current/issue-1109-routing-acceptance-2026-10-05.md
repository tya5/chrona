<!-- chrona:literal-acceptance/v1 -->
# Issue #1109 — routing acceptance

R1 candidate: local focused tests, schema equivalence and a 64-context batch pass;
19 sub-stroke segments become 0, no additional route is suppressed, and 55 pairs
remain byte-identical. Nine pairs change (HALCYON 02/11/12/15/17/18/19/20 and
Orion gates); four existing launch-leop suppression attempt reports change,
but no diagnostic or suppression is added. R1 is released on
[`b1380031`](https://github.com/tya5/chrona/commit/b1380031ab01e10c1b538d5ca28f16d3e8b7a695):
[three-OS release gate](https://github.com/tya5/chrona/actions/runs/37239790303) passed.
Layout owns reduction, terminal setbacks and axes; Scene/adapter only observe
or serialize completed values. No example or Theme adaptation.

R2 candidate: 1489 focused Layout/Scene tests and the 64-context batch pass;
0 unexplained node overlaps, 12 exactly diagnosed residual pairs, 0 new lost
routes and 0 Scene errors. 31 route geometries and 17 SVGs change; 47 SVGs stay
identical. Target-B before/after and the changed SVG batch were inspected.
Controller gains two member labels and moves one; one optional relation label
is suppressed after removing an 8px
shared approach; bounded placement improvement is [#1158](https://github.com/tya5/chrona/issues/1158).
Existing seven route suppressions remain R5. R2 merged via [#1159](https://github.com/tya5/chrona/pull/1159),
generated main `b4e00f2f`. Its [release run](https://github.com/tya5/chrona/actions/runs/37242994868)
fails on all three OS only at the stale corpus assertion requiring 22 horizontal
entries. R3 replaces that incidental count with a documented reason check for
every non-horizontal entry; release acceptance remains pending.

R3 candidate: 1511 Layout/Scene and entry-corpus tests pass; the final corridor
guard has 60 focused passing tests. The verified 64-context batch has zero Scene
errors, new lost routes, sub-stroke segments or primary-mark crossings. Five
node-overlap pairs remain precisely diagnosed. Target-B SVG before/after was
read: launch→LEOP remains straight and all 24 dependency paths remain present.
62 SVGs and 477 relation geometries change. Text changes/additions/removals are
101/4/45: removals include the optional EVB Arrival name in 38 Controller
contexts, three note indexes, two relation labels and two annotation texts.
The new minimal-bend route intersects the former name box. Exact replay proves
a legal displacement inside existing footprint/association bounds which the
8px sampling lattice misses. The published correction adds obstacle contacts,
not route rollback or a corpus/Theme workaround. [Candidate CI](https://github.com/tya5/chrona/actions/runs/37244756487)
finds seven failing tests: diagnostic detail (1), member labels (3), annotation
leaders (3), plus the conformance ratchet. Corrections and renewed batch/CI are
required before acceptance. R3 is not released; R4 and R5 remain open.

## Literal issue acceptance

### Issue #1109

- Source: [body](https://github.com/tya5/chrona/issues/1109), [R1–R5](https://github.com/tya5/chrona/issues/1109#issuecomment-5984583052)
- Observed: 2026-10-05

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | A gate with one incoming relation from the left at mid-height and one outgoing relation to a successor below: the outgoing path shares no segment with the incoming path's final segment. | met | [Synthetic node fixtures](../../../tests/unit/chrona/presentation/scene/test_relation_node_approach.py); baseline 12.4px overlap becomes 0 | — |
| 2 | The S-jog fixture: the route has the minimal bend count for its entry. | not met | [Neutral reductions](../../../tests/unit/chrona/presentation/layout/test_route_reduction.py) and [real port search](../../../tests/unit/chrona/presentation/layout/test_routing_placement.py) pass; candidate publication/release pending | — |
| 3 | A corpus Scene check reports any two relations at one node that overlap along a segment. It must be 0 after regeneration, or every remaining case is listed with a diagnostic. | met | [All-endpoint Scene observer](../../../src/chrona/presentation/scene/perceptibility.py); 64-context batch: 0 unexplained, 12 exactly diagnosed pairs | — |
| 4 | Target B: `launch → leop` leaves the gate without overlapping `frr → launch`, with no S-jog. | met | [Regenerated target B](../../../examples/halcyon-1/generated/21-target-b.scene.json) and SVG review: straight downward departure, no shared approach or S-jog | — |
| 5 | A gate source above a bar whose port x differs from the drop x by less than a stroke width emits a straight vertical first segment. | met | [Synthetic composer fixture](../../../tests/unit/chrona/presentation/scene/test_relation_round_terminals.py) | — |
| 6 | The source terminal's centre lies on the line. | met | [Synthetic centre fixtures](../../../tests/unit/chrona/presentation/scene/test_relation_round_terminals.py) and [short-gap offsets](../../../tests/unit/chrona/presentation/layout/test_relation_substroke.py) | — |
| 7 | A Scene check finds no relation segment shorter than its stroke width, corpus-wide, after regeneration. | met | [Scene observer](../../../src/chrona/presentation/scene/perceptibility.py); 64-context batch: 0 | — |
| 8 | Existing straight-start fixtures are unchanged. | met | [Straight-start tests](../../../tests/unit/chrona/presentation/scene/test_relation_terminal_none.py) and [geometry identity](../../../tests/unit/chrona/presentation/layout/test_relation_substroke.py) | — |
| 9 | Target B: the PDR source terminal sits on the line. | not met | [Target-B Theme](../../../examples/halcyon-1/themes/target-b.yaml) declares `none`, so no rendered terminal exists to assess. [Circle case](../../../tests/unit/chrona/presentation/scene/test_relation_round_terminals.py) proves the general fix, not this literal criterion; owner disposition required | — |
| 10 | synthetic fixtures for 1, 2 and 4 that fail on the previous order or rule and pass now; `tvac-emc` either enters from the side or the diagnostic names a reason that is documented as final; corpus before/after with images read. | not met | [R4](https://github.com/tya5/chrona/issues/1109#issuecomment-5984583052) remains | — |
| 11 | This issue must bring the count of relations suppressed for routing reasons back to **0** across the corpus. Every dependency must be drawn, with no route through any mark, within the existing `maxBends` and `maxDetourRatio` or with a reported, reasoned exception. | not met | [Owner R5 requirement](https://github.com/tya5/chrona/issues/1109#issuecomment-5979830960) remains | — |
| 12 | No relation segment shorter than its stroke width, corpus-wide, after regeneration. The terminal marker's axis follows the first or last segment that is at least `headLength` long, or the port normal | met | [Axis/reduction tests](../../../tests/unit/chrona/presentation/layout/test_relation_substroke.py), observer and 64-context batch | — |
| 13 | No two relations at one node overlap along a segment. The Scene check reports 0, or lists each remaining case with a diagnostic | met | [All-endpoint observer/tests](../../../tests/unit/chrona/presentation/scene/test_perceptibility.py); R3 batch: 0 unexplained, 5 diagnosed pairs; R2 [merged PR](https://github.com/tya5/chrona/pull/1159) | — |
| 14 | The S-jog fixture routes with the minimal bend count for its entry. The target-B launch → LEOP route has no S-jog | not met | [Neutral helper](../../../tests/unit/chrona/presentation/layout/test_route_reduction.py) and real-search fixtures pass; verified target-B Scene/SVG has no launch→LEOP S-jog; candidate release pending | — |
| 15 | The blocked-corridor fixtures enter from the side when a non-crossing corridor exists within `maxBends`/`maxDetourRatio`, and fall back with `I_LAYOUT_RELATION_ENTRY_FALLBACK` otherwise. Target B reaches 25/25 or names the exception | not met | [R4](https://github.com/tya5/chrona/issues/1109#issuecomment-5984583052) remains | — |
| 16 | The count of relations suppressed for routing is 0 across the corpus. No route passes through a mark, within the existing budgets or with a reported, reasoned exception | not met | [R5](https://github.com/tya5/chrona/issues/1109#issuecomment-5984583052) remains | — |

## Programme-level criteria (optional)

Keep this issue open until all rows and the exact-main release gate are met.

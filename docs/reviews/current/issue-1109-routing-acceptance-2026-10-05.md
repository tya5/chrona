<!-- chrona:literal-acceptance/v1 -->
# Issue #1109 — routing acceptance

R1 candidate: local focused tests, schema equivalence and a 64-context batch pass;
19 sub-stroke segments become 0, no additional route is suppressed, and 55 pairs
remain byte-identical. Nine pairs change (HALCYON 02/11/12/15/17/18/19/20 and
Orion gates); four existing launch-leop suppression attempt reports change,
but no diagnostic or suppression is added. Exact-main release remains pending.
Layout owns reduction, terminal setbacks and axes; Scene/adapter only observe
or serialize completed values. No example or Theme adaptation.

## Literal issue acceptance

### Issue #1109

- Source: [body](https://github.com/tya5/chrona/issues/1109), [R1–R5](https://github.com/tya5/chrona/issues/1109#issuecomment-5984583052)
- Observed: 2026-10-05

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | A gate with one incoming relation from the left at mid-height and one outgoing relation to a successor below: the outgoing path shares no segment with the incoming path's final segment. | not met | [R2](https://github.com/tya5/chrona/issues/1109#issuecomment-5984583052) remains | — |
| 2 | The S-jog fixture: the route has the minimal bend count for its entry. | not met | [R3](https://github.com/tya5/chrona/issues/1109#issuecomment-5984583052) remains | — |
| 3 | A corpus Scene check reports any two relations at one node that overlap along a segment. It must be 0 after regeneration, or every remaining case is listed with a diagnostic. | not met | [R2](https://github.com/tya5/chrona/issues/1109#issuecomment-5984583052) remains | — |
| 4 | Target B: `launch → leop` leaves the gate without overlapping `frr → launch`, with no S-jog. | not met | [R2/R3](https://github.com/tya5/chrona/issues/1109#issuecomment-5984583052) remain | — |
| 5 | A gate source above a bar whose port x differs from the drop x by less than a stroke width emits a straight vertical first segment. | met | [Synthetic composer fixture](../../../tests/unit/chrona/presentation/scene/test_relation_round_terminals.py) | — |
| 6 | The source terminal's centre lies on the line. | met | [Synthetic centre fixtures](../../../tests/unit/chrona/presentation/scene/test_relation_round_terminals.py) and [short-gap offsets](../../../tests/unit/chrona/presentation/layout/test_relation_substroke.py) | — |
| 7 | A Scene check finds no relation segment shorter than its stroke width, corpus-wide, after regeneration. | met | [Scene observer](../../../src/chrona/presentation/scene/perceptibility.py); 64-context batch: 0 | — |
| 8 | Existing straight-start fixtures are unchanged. | met | [Straight-start tests](../../../tests/unit/chrona/presentation/scene/test_relation_terminal_none.py) and [geometry identity](../../../tests/unit/chrona/presentation/layout/test_relation_substroke.py) | — |
| 9 | Target B: the PDR source terminal sits on the line. | met | Target-B Scene/SVG unchanged; current Theme declares no source terminal. [Circle case](../../../tests/unit/chrona/presentation/scene/test_relation_round_terminals.py) independently covers the original shape | — |
| 10 | synthetic fixtures for 1, 2 and 4 that fail on the previous order or rule and pass now; `tvac-emc` either enters from the side or the diagnostic names a reason that is documented as final; corpus before/after with images read. | not met | [R4](https://github.com/tya5/chrona/issues/1109#issuecomment-5984583052) remains | — |
| 11 | This issue must bring the count of relations suppressed for routing reasons back to **0** across the corpus. Every dependency must be drawn, with no route through any mark, within the existing `maxBends` and `maxDetourRatio` or with a reported, reasoned exception. | not met | [Owner R5 requirement](https://github.com/tya5/chrona/issues/1109#issuecomment-5979830960) remains | — |
| 12 | No relation segment shorter than its stroke width, corpus-wide, after regeneration. The terminal marker's axis follows the first or last segment that is at least `headLength` long, or the port normal | met | [Axis/reduction tests](../../../tests/unit/chrona/presentation/layout/test_relation_substroke.py), observer and 64-context batch | — |
| 13 | No two relations at one node overlap along a segment. The Scene check reports 0, or lists each remaining case with a diagnostic | not met | [R2](https://github.com/tya5/chrona/issues/1109#issuecomment-5984583052) remains | — |
| 14 | The S-jog fixture routes with the minimal bend count for its entry. The target-B launch → LEOP route has no S-jog | not met | [R3](https://github.com/tya5/chrona/issues/1109#issuecomment-5984583052) remains | — |
| 15 | The blocked-corridor fixtures enter from the side when a non-crossing corridor exists within `maxBends`/`maxDetourRatio`, and fall back with `I_LAYOUT_RELATION_ENTRY_FALLBACK` otherwise. Target B reaches 25/25 or names the exception | not met | [R4](https://github.com/tya5/chrona/issues/1109#issuecomment-5984583052) remains | — |
| 16 | The count of relations suppressed for routing is 0 across the corpus. No route passes through a mark, within the existing budgets or with a reported, reasoned exception | not met | [R5](https://github.com/tya5/chrona/issues/1109#issuecomment-5984583052) remains | — |

## Programme-level criteria (optional)

Keep this issue open until all rows and the exact-main release gate are met.

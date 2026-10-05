<!-- chrona:literal-acceptance/v1 -->
# Issue #1109 — routing acceptance

R1 released on `b1380031`: [three-OS gate](https://github.com/tya5/chrona/actions/runs/37239790303).
R2/R3 are merged via [#1159](https://github.com/tya5/chrona/pull/1159) and
[#1160](https://github.com/tya5/chrona/pull/1160), generated main `a7580c93`.
[Exact-head PR checks](https://github.com/tya5/chrona/actions/runs/37249881525)
passed; [exact-main release](https://github.com/tya5/chrona/actions/runs/37251039422)
passed on Ubuntu, macOS and Windows. The PR's grouped 64-context side-effect table is the batch evidence:
no lost routes or member-name identities; 32 gained relation labels; one replaced
annotation summary and two lost optional TVAC indices. Paired target-B,
Controller and Editorial-lanes renders were inspected. Layout owns all geometry,
measurement and routes; Scene/adapter only project/serialize. No corpus/Theme
adaptation, relaxed safety test or increased search/quality budget.
R5 and the literal PDR no-marker disposition remain open.

R4 released via [#1161](https://github.com/tya5/chrona/pull/1161), generated main
`12727eba`; [three-OS release](https://github.com/tya5/chrona/actions/runs/37253418209)
passed. 55 focused entry/port/node/ghost/corpus tests pass, including
Project/ActualSet fixtures and prior-rule mutations. Target-B surfaces and SVG
are byte-identical; only four final reasons change to `node-approach-conflict`.
TVAC retains `entry-stub-blocked`: its detached EMC ghost ends at x990.127,
past the required 10px stub tip x989.182. The existing node-clearance ranking
remains; round-head paint trimming no longer invalidates semantic entry.
The exact-head 137-path CI batch proves all 64 SVGs and all Scene geometry
identical; only the four target-B reasons and diagnostic source line numbers change.

## Literal issue acceptance

R5 candidate in [#1162](https://github.com/tya5/chrona/pull/1162), not release-accepted:
the [corrected exact-head batch](https://github.com/tya5/chrona/pull/1162#issuecomment-5987677842)
has 64 contexts, 627→634 paths, routing suppressions 7→0, names 526→542
(zero lost), unchanged 257 annotation identities and zero Scene safety errors.
All seven restored paths meet max4 bends/ratio2. Paired rendered output was
inspected. Seven optional note indices disappear with explicit diagnostics;
four note bodies show the declared status; two new overflow warnings leave
existing status paint unchanged. Conformance and newest-Python reproduction
pass; seven CLI/ownership/wiring expectation failures still require a green
exact-head run. One bounded Layout recovery preserves names, relation status
and relation labels without replay or relaxed quality/safety. No corpus/Theme
adaptation. Merge and exact-main three-OS release remain required.

### Issue #1109

- Source: [body](https://github.com/tya5/chrona/issues/1109), [R1–R5](https://github.com/tya5/chrona/issues/1109#issuecomment-5984583052)
- Observed: 2026-10-05

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | A gate with one incoming relation from the left at mid-height and one outgoing relation to a successor below: the outgoing path shares no segment with the incoming path's final segment. | met | [Synthetic node fixtures](../../../tests/unit/chrona/presentation/scene/test_relation_node_approach.py); baseline 12.4px overlap becomes 0 | — |
| 2 | The S-jog fixture: the route has the minimal bend count for its entry. | met | [Neutral reductions](../../../tests/unit/chrona/presentation/layout/test_route_reduction.py) and [real port search](../../../tests/unit/chrona/presentation/layout/test_routing_placement.py); #1160 merged, exact-main release 37251039422 passed | — |
| 3 | A corpus Scene check reports any two relations at one node that overlap along a segment. It must be 0 after regeneration, or every remaining case is listed with a diagnostic. | met | [All-endpoint Scene observer](../../../src/chrona/presentation/scene/perceptibility.py); 64-context R3 batch: 0 unexplained, 5 exactly diagnosed pairs | — |
| 4 | Target B: `launch → leop` leaves the gate without overlapping `frr → launch`, with no S-jog. | met | [Regenerated target B](../../../examples/halcyon-1/generated/21-target-b.scene.json) and SVG review: straight downward departure, no shared approach or S-jog | — |
| 5 | A gate source above a bar whose port x differs from the drop x by less than a stroke width emits a straight vertical first segment. | met | [Synthetic composer fixture](../../../tests/unit/chrona/presentation/scene/test_relation_round_terminals.py) | — |
| 6 | The source terminal's centre lies on the line. | met | [Synthetic centre fixtures](../../../tests/unit/chrona/presentation/scene/test_relation_round_terminals.py) and [short-gap offsets](../../../tests/unit/chrona/presentation/layout/test_relation_substroke.py) | — |
| 7 | A Scene check finds no relation segment shorter than its stroke width, corpus-wide, after regeneration. | met | [Scene observer](../../../src/chrona/presentation/scene/perceptibility.py); 64-context batch: 0 | — |
| 8 | Existing straight-start fixtures are unchanged. | met | [Straight-start tests](../../../tests/unit/chrona/presentation/scene/test_relation_terminal_none.py) and [geometry identity](../../../tests/unit/chrona/presentation/layout/test_relation_substroke.py) | — |
| 9 | Target B: the PDR source terminal sits on the line. | not met | [Target-B Theme](../../../examples/halcyon-1/themes/target-b.yaml) declares `none`, so no rendered terminal exists to assess. [Circle case](../../../tests/unit/chrona/presentation/scene/test_relation_round_terminals.py) proves the general fix, not this literal criterion; owner disposition required | — |
| 10 | synthetic fixtures for 1, 2 and 4 that fail on the previous order or rule and pass now; `tvac-emc` either enters from the side or the diagnostic names a reason that is documented as final; corpus before/after with images read. | met | [Project fixtures and prior-rule mutations](../../../tests/unit/chrona/presentation/scene/test_relation_entry_acceptance.py); detached-ghost final reason in Spec50; all 64 SVGs unchanged from inspected R3 renders; #1161 exact batch and release 37253418209 passed | — |
| 11 | This issue must bring the count of relations suppressed for routing reasons back to **0** across the corpus. Every dependency must be drawn, with no route through any mark, within the existing `maxBends` and `maxDetourRatio` or with a reported, reasoned exception. | not met | [Owner R5 requirement](https://github.com/tya5/chrona/issues/1109#issuecomment-5979830960) remains | — |
| 12 | No relation segment shorter than its stroke width, corpus-wide, after regeneration. The terminal marker's axis follows the first or last segment that is at least `headLength` long, or the port normal | met | [Axis/reduction tests](../../../tests/unit/chrona/presentation/layout/test_relation_substroke.py), observer and 64-context batch | — |
| 13 | No two relations at one node overlap along a segment. The Scene check reports 0, or lists each remaining case with a diagnostic | met | [All-endpoint observer/tests](../../../tests/unit/chrona/presentation/scene/test_perceptibility.py); R3 batch: 0 unexplained, 5 diagnosed pairs; R2 [merged PR](https://github.com/tya5/chrona/pull/1159) | — |
| 14 | The S-jog fixture routes with the minimal bend count for its entry. The target-B launch → LEOP route has no S-jog | met | [Neutral helper](../../../tests/unit/chrona/presentation/layout/test_route_reduction.py) and real-search fixtures; verified target-B has no S-jog; #1160 merged, exact-main release 37251039422 passed | — |
| 15 | The blocked-corridor fixtures enter from the side when a non-crossing corridor exists within `maxBends`/`maxDetourRatio`, and fall back with `I_LAYOUT_RELATION_ENTRY_FALLBACK` otherwise. Target B reaches 25/25 or names the exception | met | [R4 fixtures](../../../tests/unit/chrona/presentation/scene/test_relation_entry_acceptance.py); target-B has 24 semantic dependencies and a legend swatch, with four named node-approach exceptions and one detached-ghost stub exception; #1161 and release 37253418209 passed | — |
| 16 | The count of relations suppressed for routing is 0 across the corpus. No route passes through a mark, within the existing budgets or with a reported, reasoned exception | not met | [R5](https://github.com/tya5/chrona/issues/1109#issuecomment-5984583052) remains | — |

## Programme-level criteria (optional)

Keep this issue open until all rows and the exact-main release gate are met.

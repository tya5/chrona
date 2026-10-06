<!-- chrona:literal-acceptance/v1 -->
# Issue #1109 — routing acceptance

Published slices: R1 `b1380031` ([release](https://github.com/tya5/chrona/actions/runs/37239790303));
R2/R3 via [#1159](https://github.com/tya5/chrona/pull/1159)/[#1160](https://github.com/tya5/chrona/pull/1160),
`a7580c93` ([release](https://github.com/tya5/chrona/actions/runs/37251039422));
R4 via [#1161](https://github.com/tya5/chrona/pull/1161), `12727eba`
([release](https://github.com/tya5/chrona/actions/runs/37253418209)). All three-OS gates passed.
Layout retains geometry, measurement and routing ownership; Scene/adapter project/serialize.
No corpus/Theme adaptation, relaxed safety contract or increased search/quality budget.

## Literal issue acceptance

R5 released via [#1162](https://github.com/tya5/chrona/pull/1162), source `977dd517`, generated main `7d2b41a2`:
the [corrected exact-head batch](https://github.com/tya5/chrona/pull/1162#issuecomment-5987677842)
has 64 contexts, 627→634 paths, routing suppressions 7→0, names 526→542
(zero lost), unchanged 257 annotation identities and zero Scene safety errors.
All seven restored paths meet max4 bends/ratio2. Paired rendered output was
inspected. Seven optional note indices disappear with explicit diagnostics;
four note bodies show the declared status; two new overflow warnings leave
existing status paint unchanged. Conformance and newest-Python reproduction
pass; [final exact-head CI](https://github.com/tya5/chrona/actions/runs/37261236812)
passed every required check, including all three pytest shards. One bounded Layout recovery preserves names, relation status
and relation labels without replay or relaxed quality/safety. No corpus/Theme
adaptation. Generated main `7d2b41a2` matches all 137 audited snapshot files byte-for-byte;
[derived gate](https://github.com/tya5/chrona/actions/runs/37263751733) passed.
[Exact-main three-OS release](https://github.com/tya5/chrona/actions/runs/37264464241)
passed, including full pytest, conformance, wheel/smoke, MCP floor and newest-Python reproduction.
R4a/R4b/R6 passed their final release. The [reviewer disposition](https://github.com/tya5/chrona/issues/1109#issuecomment-6005940739)
accepts row9's general synthetic evidence; its actual Target B marker check is
not applicable because the approved target declares no source terminal.

### Issue #1109

- Source: [body](https://github.com/tya5/chrona/issues/1109), [R1–R5](https://github.com/tya5/chrona/issues/1109#issuecomment-5984583052)
- Observed: 2026-10-06

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | A gate with one incoming relation from the left at mid-height and one outgoing relation to a successor below: the outgoing path shares no segment with the incoming path's final segment. | met | [Synthetic node fixtures](../../../tests/unit/chrona/presentation/scene/test_relation_node_approach.py); baseline 12.4px overlap becomes 0 | — |
| 2 | The S-jog fixture: the route has the minimal bend count for its entry. | met | [Neutral reductions](../../../tests/unit/chrona/presentation/layout/test_route_reduction.py) and [real port search](../../../tests/unit/chrona/presentation/layout/test_routing_placement.py); #1160 merged, exact-main release 37251039422 passed | — |
| 3 | A corpus Scene check reports any two relations at one node that overlap along a segment. It must be 0 after regeneration, or every remaining case is listed with a diagnostic. | met | [All-endpoint Scene observer](../../../src/chrona/presentation/scene/perceptibility.py); current 64-context batch: 0 unexplained, 4 diagnosed pairs | — |
| 4 | Target B: `launch → leop` leaves the gate without overlapping `frr → launch`, with no S-jog. | met | [Regenerated target B](../../../examples/halcyon-1/generated/21-target-b.scene.json) and SVG review: straight downward departure, no shared approach or S-jog | — |
| 5 | A gate source above a bar whose port x differs from the drop x by less than a stroke width emits a straight vertical first segment. | met | [Synthetic composer fixture](../../../tests/unit/chrona/presentation/scene/test_relation_round_terminals.py) | — |
| 6 | The source terminal's centre lies on the line. | met | [Synthetic centre fixtures](../../../tests/unit/chrona/presentation/scene/test_relation_round_terminals.py) and [short-gap offsets](../../../tests/unit/chrona/presentation/layout/test_relation_substroke.py) | — |
| 7 | A Scene check finds no relation segment shorter than its stroke width, corpus-wide, after regeneration. | met | [Scene observer](../../../src/chrona/presentation/scene/perceptibility.py); 64-context batch: 0 | — |
| 8 | Existing straight-start fixtures are unchanged. | met | [Straight-start tests](../../../tests/unit/chrona/presentation/scene/test_relation_terminal_none.py) and [geometry identity](../../../tests/unit/chrona/presentation/layout/test_relation_substroke.py) | — |
| 9 | Target B: the PDR source terminal sits on the line. | met | [Explicit reviewer disposition](https://github.com/tya5/chrona/issues/1109#issuecomment-6005940739): the approved no-source-terminal Target B makes the target-specific check not applicable; [round-terminal fixtures](../../../tests/unit/chrona/presentation/scene/test_relation_round_terminals.py) and [non-degenerate axis tests](../../../tests/unit/chrona/presentation/layout/test_relation_substroke.py) meet the retained general rule | — |
| 10 | synthetic fixtures for 1, 2 and 4 that fail on the previous order or rule and pass now; `tvac-emc` either enters from the side or the diagnostic names a reason that is documented as final; corpus before/after with images read. | met | [Synthetic regressions](../../../tests/unit/chrona/presentation/scene/test_relation_entry_acceptance.py) pass; local actual SVG has TVAC side entry. [Final corpus](https://github.com/tya5/chrona/pull/1168#issuecomment-5995552142) and [exact-main release](https://github.com/tya5/chrona/actions/runs/37338249489) passed | — |
| 11 | This issue must bring the count of relations suppressed for routing reasons back to **0** across the corpus. Every dependency must be drawn, with no route through any mark, within the existing `maxBends` and `maxDetourRatio` or with a reported, reasoned exception. | met | [64-context actual artifact audit](https://github.com/tya5/chrona/pull/1162#issuecomment-5987677842): 634 dependency paths, 0 routing suppressions/Scene safety errors; seven restorations meet max4 bends/ratio2, no exceptions or budget changes. All 137 published files match audited bytes; [exact-main release](https://github.com/tya5/chrona/actions/runs/37264464241) passed | — |
| 12 | No relation segment shorter than its stroke width, corpus-wide, after regeneration. The terminal marker's axis follows the first or last segment that is at least `headLength` long, or the port normal | met | [Axis/reduction tests](../../../tests/unit/chrona/presentation/layout/test_relation_substroke.py), observer and 64-context batch | — |
| 13 | No two relations at one node overlap along a segment. The Scene check reports 0, or lists each remaining case with a diagnostic | met | [All-endpoint observer/tests](../../../tests/unit/chrona/presentation/scene/test_perceptibility.py); current 64-context batch: 0 unexplained, 4 diagnosed pairs; R2 [merged PR](https://github.com/tya5/chrona/pull/1159) | — |
| 14 | The S-jog fixture routes with the minimal bend count for its entry. The target-B launch → LEOP route has no S-jog | met | [Neutral helper](../../../tests/unit/chrona/presentation/layout/test_route_reduction.py) and real-search fixtures; verified target-B has no S-jog; #1160 merged, exact-main release 37251039422 passed | — |
| 15 | The blocked-corridor fixtures enter from the side when a non-crossing corridor exists within `maxBends`/`maxDetourRatio`, and fall back with `I_LAYOUT_RELATION_ENTRY_FALLBACK` otherwise. Target B reaches 25/25 or names the exception | met | [Entry regressions](../../../tests/unit/chrona/presentation/scene/test_relation_entry_acceptance.py) and [actual SVG fan-in tests](../../../tests/unit/chrona/presentation/scene/test_relation_fan_in.py); local Target-B 24/24 semantic dependencies side-enter (the 25th Path is the legend). [Final corpus](https://github.com/tya5/chrona/pull/1168#issuecomment-5995552142) and [exact-main release](https://github.com/tya5/chrona/actions/runs/37338249489) passed | — |
| 16 | The count of relations suppressed for routing is 0 across the corpus. No route passes through a mark, within the existing budgets or with a reported, reasoned exception | met | Same full-corpus evidence as row 11; [search/quality regressions](../../../tests/unit/chrona/presentation/layout/test_relation_search_candidates.py); [exact-main release](https://github.com/tya5/chrona/actions/runs/37264464241) passed | — |
| 17 | generate gate and bar bottom or top egress followed by a horizontal entry, and do not classify it as `node-approach-conflict` unless it overlaps another relation at that node. Acceptance: on synthetic fixtures and on target B, `delivery-integration` enters from the side. | met | [Neutral bottom-egress fixtures](../../../tests/unit/chrona/presentation/scene/test_relation_entry_acceptance.py) pass; local actual SVG delivery side-enters with bustest through approved R6. [Final corpus](https://github.com/tya5/chrona/pull/1168#issuecomment-5995552142) and [exact-main release](https://github.com/tya5/chrona/actions/runs/37338249489) passed | — |
| 18 | the entry-stub requirement is head length + clearance, with the corner radius counted once, at the turn before the stub. Acceptance: with radius 4 and head 6, `launch-leop` and `tvac-emc` enter from the side on target B. Fixtures cover each radius from 0 to 6. | met | [R4b fixtures](../../../tests/unit/chrona/presentation/scene/test_relation_entry_acceptance.py): radius sweep, head tangent and genuine blocker; local Target-B has both side entries. [Exact-head batch audit](https://github.com/tya5/chrona/pull/1168#issuecomment-5994763856); [exact-main release](https://github.com/tya5/chrona/actions/runs/37338249489) passed | — |
| 19 | relations that end at the same target port may share their final approach and draw one arrowhead, like Graphviz `samehead`, as the mock does. Sharing is allowed only among arrivals at the same port, and every other overlap stays forbidden. Acceptance: `station-comms` and `avionics-bustest` enter from the side together with `mcs-comms` and `eps-bustest`. Target B reaches 24/24 side entries. | met | [Actual SVG/composer regressions](../../../tests/unit/chrona/presentation/scene/test_relation_fan_in.py), [reference and observer guards](../../../tests/unit/chrona/presentation/scene/test_fan_in_metadata.py); local Target-B 24/24 side entries and four groups with one SVG head each. [Final corpus](https://github.com/tya5/chrona/pull/1168#issuecomment-5995552142) and [exact-main release](https://github.com/tya5/chrona/actions/runs/37338249489) passed | — |

New [reviewer requirements](https://github.com/tya5/chrona/issues/1109#issuecomment-5993655643)
supersede the previous R4 exception-only acceptance in rows 10/15.
R4b design/architecture/implementation: [current plan](https://github.com/tya5/chrona/issues/1109#issuecomment-5994383796).
No Project/View/Theme edits; Layout owns completed geometry, Scene projects it and adapters serialize.
Full-radius clearance remains preferred; blocked corridors may clip the turn, never the head or mandatory clearance.
The finite source-egress back-route candidates use the unchanged safety and quality gates.

R6 [pre-code plan and architecture review](https://github.com/tya5/chrona/issues/1109#issuecomment-5994954912)
completes R4a/R4b in the same PR. Layout alone groups compatible resolved-port
arrivals and chooses the first declared head owner; optional Scene-v0.7 metadata
records the decision. Scene validates references and independently observes
arrival geometry; no adapter infers ports or recomputes placement. Spec08/50
are updated. Negative tests retain arrival/departure and other-port safety.
Focused combined tests: 169 passed; entry/endpoint/terminal/SVG tests: 55 passed.
Schema-equivalence L1/L2/L3 and 31 gate tests pass.
R4a/R4b/R6 are published through [#1168](https://github.com/tya5/chrona/pull/1168),
source `c07e4dc2`, generated main `e5b3691f`. [All required final-head checks](https://github.com/tya5/chrona/actions/runs/37321570670)
and [generated-main gate](https://github.com/tya5/chrona/actions/runs/37326035866) passed.
The [full actual-SVG batch audit](https://github.com/tya5/chrona/pull/1168#issuecomment-5995552142)
retains 10,496 primitive identities, 634 dependencies and 542 member names across 64 contexts;
33 relation routes change and 28 duplicate heads disappear, with no nonrelation changes,
route suppressions or relation safety errors. Every fan-in group retains its SVG paths
and exactly one head; all 15 changed-context renders were inspected. Target B has 24/24
horizontal arrivals and zero fallbacks. [All 137 published files](https://github.com/tya5/chrona/issues/1109#issuecomment-5987113298)
match the audited final snapshot byte-for-byte.

[Exact-main release 37327000794](https://github.com/tya5/chrona/actions/runs/37327000794)
exposes an obsolete corpus test requiring the five pre-R4b/R6 fallbacks, not a routing regression.
The correction in [#1171](https://github.com/tya5/chrona/pull/1171) requires all 24 rendered
dependencies to side-enter, including the restored named paths, and zero fallback diagnostics.
Focused verification: `.venv/bin/python -m pytest -q tests/integration/test_entry_side_corpus.py`
— **2 passed**, rendering the unmodified actual Target B twice. It changes no product or corpus resources.
The [current Status](https://github.com/tya5/chrona/issues/1109#issuecomment-5987113298)
records focused verification, each failed OS check and replacement release evidence.
That failed run is superseded by the successful replacement release below.

Replacement [exact-main release37338249489](https://github.com/tya5/chrona/actions/runs/37338249489)
passed on published `8f5de096e3601507639a9ec3b3a145656159b7c5`, including
three-OS full pytest/conformance/wheel-smoke, MCP floor and newest-Python
materializers. All137 public files match the final reviewed snapshot. This
proves rows10/15/17/18/19. The [later exact-main release](https://github.com/tya5/chrona/actions/runs/37386692014)
also passed on `82e74cae250a9ed7fe31bce8b45da7a597f8dde4` with all routing
changes and this review present. Row9 is accepted under the explicit disposition
linked above; no target YAML or general terminal contract changes.

## Programme-level criteria (optional)

All literal rows are met under the linked dispositions. The closing receipt
must cite the successful exact-main release containing this review update.

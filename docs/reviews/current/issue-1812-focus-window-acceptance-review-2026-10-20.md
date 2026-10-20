# Issue 1812 — focus-window acceptance

Status: implementation and parked-head artifact verified; final-base CI/release pending.
Source: `f6e9802fe`; integrated trusted ready `ec8f27ed3` at `79de8b64e`.
Design: [living issue record](https://github.com/tya5/chrona/issues/1812#issuecomment-6286331161),
published specifications `7b2752dae` and row-absence correction `85756e601`.

| Literal acceptance criterion | Verdict | Evidence |
| --- | --- | --- |
| Synthetic tests for each of the three rules, plus PNGs. | met | `test_completion.py`, `test_view_completion_window.py`, `test_projection_rows.py`, `test_focus_window_render.py`; inspected [finished](assets-1812/finished.png), [relative](assets-1812/relative.png), [combined focus](assets-1812/focus.png). Synthetic row counts: 2 / 3 / 1. |
| A guide section "focus a slide: hide finished work, show the next N weeks" checked by the docs tests. | met | [Executable guide](../../guides/update-a-plan.md); `test_update_a_plan_guide.py` executes its literal command and checks kept/omitted labels and the identified dependency warning: 5 passed. |
| Existing Views are unchanged (count table). | not met | Automatic/fixed-lane implicit-default versus explicit-keep Scene and SVG identity tests pass. Official parked-head audit below proves all 50 pairs unchanged; final-base artifact verification remains pending. |

Whole-architecture review: Core owns Actual completion; View owns selection and
relative dates; one projection-bound Layout admission owns geometry compaction.
Original sources, membership and relations remain intact. Scene v0.7 projects
completed row-absence facts; adapters neither select rows nor fabricate ports.
Independent Luna review and native automatic/lane/folded tests found and verified
the resolved-empty-row routing fix. Required forecast labels retain their existing
fit contract. Missing as-of is a pointed `/body/window` diagnostic at the public
use-case boundary, not merely a message containing a path.

Verification: semantic/schema/frontend batch 342 passed; Scene/Layout batch 195
passed; root integration/projection batch 73 passed; schema/docs batch 177 passed;
diagnostic/failure-report batch 40 passed (overlapping suites, not additive).
Full schema equivalence passes (2 deliberate L1 changes, 42 equal; existing five
invalid L2/L3 fixtures unchanged); inventory and explicit Scene delivery pass.
Initial conformance identified two authored omissions (schema examples and Scene
delivery registration), now corrected with focused checks. Diagnostic inventory
and presentation coverage are stale generated reports, delegated to the official
CI snapshot rather than authored here; all other initial conformance checks passed.
Official parked-head run [39402774549](https://github.com/tya5/chrona/actions/runs/39402774549),
head `e8175242e`, artifact `12256001890`, SHA256
`185baa0021f900e3af83d75834c8a27eb8ac3715dc50bab44b94621379fa0600`:

| Scope | SVG changed | Scene changed | Primitives/routes/labels/diagnostics added, removed or changed |
| --- | --- | --- | --- |
| All 50 declared slides | 0/50 | 0/50 | 0 for every slide |

All 109 paths remain present, with no additions/retirements. Only generated
diagnostic source anchors/new guard catalog entries and coverage vocabulary/probes
change. Conformance, public materializers and newest-Python checks pass. All three
pytest shards were inventoried: seven stale synthetic-fixture/schema expectations,
corrected by tests-only `fd3c8ae47`; the affected six modules pass 134 tests without
product fallbacks or validator weakening.

CI supplies full tests and release evidence. Follow the ready main containing
[1818](https://github.com/tya5/chrona/issues/1818), then verify the final-base artifact
and exact-main three-OS release. Parked-head evidence alone does not close the issue.

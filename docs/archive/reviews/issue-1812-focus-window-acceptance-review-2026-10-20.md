# Issue 1812 — focus-window acceptance

Status: accepted and closed; all three literal rows and exact-main release complete.
Source: `f6e9802fe`; integrated trusted ready `27d2fd8f2` at `4d47de165`.
Design: [living issue record](https://github.com/tya5/chrona/issues/1812#issuecomment-6286331161),
published specifications `7b2752dae` and row-absence correction `85756e601`.

| Literal acceptance criterion | Verdict | Evidence |
| --- | --- | --- |
| Synthetic tests for each of the three rules, plus PNGs. | met | `test_completion.py`, `test_view_completion_window.py`, `test_projection_rows.py`, `test_focus_window_render.py`; inspected [finished](assets-1812/finished.png), [relative](assets-1812/relative.png), [combined focus](assets-1812/focus.png). Synthetic row counts: 2 / 3 / 1. |
| A guide section "focus a slide: hide finished work, show the next N weeks" checked by the docs tests. | met | [Executable guide](../../guides/update-a-plan.md); `test_update_a_plan_guide.py` executes its literal command and checks kept/omitted labels and the identified dependency warning: 5 passed. |
| Existing Views are unchanged (count table). | met | Automatic/fixed-lane implicit-default versus explicit-keep Scene and SVG identity tests pass. Final PR artifact below proves all 50 pairs unchanged. |

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
Final PR run [39410405412](https://github.com/tya5/chrona/actions/runs/39410405412),
head `7dd6a1ae7`, artifact `12258449372`, SHA-256
`a4399d944f552ff74233ee00c87fc81b4b3f1b37e0d043439c1540449e5d7247`:

| Scope | SVG changed | Scene changed | Primitives/routes/labels/diagnostics added, removed or changed |
| --- | --- | --- | --- |
| All 50 declared slides | 0/50 | 0/50 | 0 for every slide |

All 109 paths remain present, with no additions/retirements. Only generated
diagnostic source anchors, new guard catalog entries, and coverage vocabulary/
probes change. All final PR checks pass. All three pytest shards were inventoried:
seven stale synthetic-fixture/schema expectations, corrected by tests-only
`fd3c8ae47`; the affected six modules pass 134 tests without product fallbacks or
validator weakening.

Integration with [1818](https://github.com/tya5/chrona/issues/1818) preserves both
row admission and declared precision through the shared Layout request/preflight.
Window/precision/guide tests pass 61 cases; defaults/chip/lane tests pass 82 cases
(overlapping suites); the three prior-failure fixture modules also pass 31 tests
after integration. Exact review-containing main run
[39413307476](https://github.com/tya5/chrona/actions/runs/39413307476) at
`3d028adedebcf377d36fb9e1d7e983f0c858e074` passed full pytest, conformance and
wheel/smoke on macOS, Ubuntu and Windows, plus MCP floor and newest-Python
reproduction. [Closing acceptance](https://github.com/tya5/chrona/issues/1812#issuecomment-6290241604).

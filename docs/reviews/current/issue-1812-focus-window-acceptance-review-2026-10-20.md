# Issue 1812 — focus-window acceptance

Status: implementation verified; official PR artifact and exact-main release pending.
Source: `f6e9802fe`; integrated trusted ready `ec8f27ed3` at `79de8b64e`.
Design: [living issue record](https://github.com/tya5/chrona/issues/1812#issuecomment-6286331161),
published specifications `7b2752dae` and row-absence correction `85756e601`.

| Literal acceptance criterion | Verdict | Evidence |
| --- | --- | --- |
| Synthetic tests for each of the three rules, plus PNGs. | met | `test_completion.py`, `test_view_completion_window.py`, `test_projection_rows.py`, `test_focus_window_render.py`; inspected [finished](assets-1812/finished.png), [relative](assets-1812/relative.png), [combined focus](assets-1812/focus.png). Synthetic row counts: 2 / 3 / 1. |
| A guide section "focus a slide: hide finished work, show the next N weeks" checked by the docs tests. | met | [Executable guide](../../guides/update-a-plan.md); `test_update_a_plan_guide.py` executes its literal command and checks kept/omitted labels and the identified dependency warning: 5 passed. |
| Existing Views are unchanged (count table). | not met | Automatic/fixed-lane implicit-default versus explicit-keep Scene and SVG identity tests pass. Final official corpus byte/count table remains pending; do not infer it from synthetic tests. |

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
CI supplies full tests, materializer counts and release evidence. Independent
macOS byte-reproduction failure [1818](https://github.com/tya5/chrona/issues/1818)
remains unresolved; this review does not claim release acceptance or issue closure.

# Issue 1792 — acceptance review

Row 1 source: `4668b7173e8f41ab14de28fd0683729620592778`.
Design/architecture/plan: [selected rule](https://github.com/tya5/chrona/issues/1792#issuecomment-6281002267),
[trial-observation clarification](https://github.com/tya5/chrona/issues/1792#issuecomment-6281081635).
Normative authority: Spec 50 §3.3; user guidance: `skills/chrona/references/diagnostics.md`.

| Literal issue acceptance | Status | Direct evidence |
| --- | --- | --- |
| Base the threshold on the measured cost model from #1734's phase data, or on candidate work rather than pairs. State it in diagnostics.md. The 150-task input triggers the warning on target-b. | met; released | [Measurements and primary inputs](assets-1792/README.md); documented 2,370 potential normal connector-port-pair threshold; [actual 150-task render](assets-1792/target-b-receipt.md) warns at 2,388, with unchanged SVG and only one additional Scene diagnostic. Exact-main release below passed. |
| Identity is checked at the command, and the agent-interface guide covers both flows. | met; released | [PR1805](https://github.com/tya5/chrona/pull/1805) checks an existing preset's id/version before mutation. `test_select_preset_refuses_a_binding_the_pinned_preset_cannot_render` covers both mismatches, unchanged bytes/revision, continued rendering and a matching re-pin. `docs/guides/agent-interface.md` covers switching and undoing an added task by recreating the bundle without it. |
| The guide defines depth, the recipe works on both plan shapes, and the header uses a wording key. | met; released | Same PR: `docs/guides/executive-summary.md` defines top-level depth0, direct-child depth1 and `all`; the nested/grouped-only recipes use1/0 respectively. `test_executive_summary_guide.py` renders both shapes and en-US/ja-JP `{wording: column.task}` headers. |

Architecture review: Layout prepares and consumes the same ordered candidate
domains before expensive search. Recovery still uses live obstacles; route policy,
budgets, ordering, hints and geometry are unchanged. The use case retains the
first qualifying attempt's typed advisory independently of a fallible observer;
trial phase/count events remain buffered. Scene/adapters only carry/serialize it.

Focused verification: 222 passed in 70.46 s across render-review, route
preparation/workload, count closure, windows, hints, preferred routes, relation
resolution/budgets, progress/model/CLI-MCP feedback, and declared/critical route
integration modules. Covers rejected-trial early delivery, one emission, observer
failure/no-observer invariance, threshold boundaries and port cardinality.
The actual render receipt reports diagnostic/geometry counts without waiving
existing diagnostics or inventing a speed guarantee.

Independent source audit found no actionable defect. After integrating1791,
the shared render boundary preserves its typed Network errors and the internal
advisory collector. The combined render-review/CLI-MCP feedback/Network guide/
View-default/CLI regression batch passes **283 tests in 228.97 s**. Integration
checkpoint `4a3fba702` includes trusted ready main `b1a3f6430`; only the generated
inventory from that main merge is inherited, never authored by this slice.

Row1 release: PR1796 merged at `657abb77e04813f9b82d96ce5d304f27c967bd3e`;
PR CI39355598420 passed and the official109-path snapshot kept50SVG/50Scene
unchanged. The exact review-containing main
`46f5d38daff5fdd511345b72ad0b9e959d4cdf42` passed
[native release39357390608](https://github.com/tya5/chrona/actions/runs/39357390608):
all three OS full pytest/conformance/wheel, MCP and newest-Python reproduction.
Rows2–3 source merged in PR1805 at
`e9aeef54e1c5f5b96d96016dafaebf20234c0d24`; its required PR checks passed.
Independent review and the combined local authoring/lifecycle/guide batch passed
17 tests after integration. The existing application command owner performs
identity admission; the guide's depth and wording use existing View contracts.
No new schema, rendering policy or layer ownership is introduced. Missing preset
documents retain the existing render-time resolution boundary.
The exact updated-review-containing main `37b3f5a988833b929509dfee3224e285bc2d51b2`
passed [release39382911887](https://github.com/tya5/chrona/actions/runs/39382911887):
all three OS full pytest/conformance/wheel, MCP floor and newest-Python
reproduction. The release was independently verified and all three literal rows
were accepted in [the closing review](https://github.com/tya5/chrona/issues/1792#issuecomment-6286049580).

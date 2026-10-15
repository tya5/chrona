# Issue 1490 acceptance review

Implementation: `f0dc77be3`, `00c8cbfc4`.
[Design/architecture/implementation plan](../planning/issue-1490-temporal-inline-capacity-work-record-2026-10-15.md).
[PR1550](https://github.com/tya5/chrona/pull/1550) merged as `df2304444`;
exact head `408a73446` passed [CI38729465143](https://github.com/tya5/chrona/actions/runs/38729465143).
Combined review-containing ready main `787eeea8f1e1e5fbeab0a4cc89ca5f4d65f85854`
passed [release38733015984](https://github.com/tya5/chrona/actions/runs/38733015984):
Ubuntu/macOS/Windows full pytest, conformance and wheel/smoke, MCP floor and
newest-Python public materializers. All literal rows are met; issue1490 is closed.

| Literal scope / acceptance | Status | Evidence |
| --- | --- | --- |
| Decide before code: natural-demand completion or retained refusal naming the slot and required inline width | met | Published design814bcb41e and plan35b5818c2 choose B; Spec33/50 and ADR0031 distinguish degenerate mapping from valid overflow. Diagnostic includes slot, allocated width, natural width and exact native point insets. |
| Carry capacity facts typed into Layout composition; do not guess growability downstream | met | TemporalInlineCapacity seals allocation and existing measured source demand at the request boundary; both native footprint owners close it before final scale/frame validation. Scene/adapters unchanged. |
| Use no epsilon and no numeric floor taken from the cases | met | Existing natural preferred width supplies measurement-only prototypes; native float mapping determines usability. No threshold, project branch, flex-minimum or canvas change. |
| Synthetic bounded and unbounded tests cover the chosen rule | met | test_temporal_capacity_hosts.py solves both host declarations; unit/native tests cover zero span/point/lane, point insets, missing typed facts and positive fitting controls. |
| #1474's 21 recorded refusal cases either render or still refuse with the chosen diagnostic, and the matrix expectations are updated to match | met | Batched existing matrix helpers: original21 and4 roadmap additions all produce exact E_LAYOUT_TEMPORAL_INLINE_CAPACITY records; public CLI batch:26 fitting controls rendered,25 expected refusals,0 failures. Ledger compares complete status/diagnostics/exit code. |
| Do not edit examples/** | met | Source/test/spec/ledger/review-only diff; no examples or generated artifact patches. |

Local commands: worktree `.venv/bin/python -m pytest -q --tb=line
tests/unit/chrona/presentation/layout tests/unit/chrona/presentation/scene
-m 'not corpus'` →3829 passed,3 deselected; matrix/capacity focused batch
→34 passed; final capacity/arithmetic batch→21 passed. The existing
`_ordered_map(_survey_context, ...,4)` surveyed all17 affected Context groups
in API and CLI modes, preserving all three viewports and fitting controls.

Architecture: no new ownership or ancestry framework. Allocation is unchanged;
Layout alone owns natural demand, native measurement and diagnostics. Positive
lane arithmetic and ordinary scale construction are preserved; natural-width
prototypes cannot become completed Scene geometry. Full pytest/conformance,
wheel/smoke and materializer evidence come from the exact-main release above,
not inferred from local tests.

Exact-head [artifact11969932896](https://github.com/tya5/chrona/actions/runs/38729465143/artifacts/11969932896)
contains109 before/after members: all50 SVGs and50 Scenes are byte-identical,
with no additions/retirements; only the diagnostic inventory changes. The
integration assertion now requires the capacity code and slot/width detail;
all final PR checks pass without relaxing the product rule.

Additional review found that the initial capacity producer incorrectly rejected
accepted ordinary repeated-source slots. Capacity now consumes the same manifest
source selection as native allocation; missing timeline and lane source-identity
errors retain their owners. Four regressions cover selected slot/width, completed
positive geometry, missing source and lane duplicates. This restores the approved
unchanged-positive-output contract without a schema or cardinality-policy change.

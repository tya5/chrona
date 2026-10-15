# Issue 1490 acceptance review

Implementation: `f0dc77be3`, `00c8cbfc4`.
[Living design/architecture/implementation plan](../../planning/active/issue-1490-temporal-inline-capacity-work-record-2026-10-15.md).
Release: pending current-head PR CI, batched public SVG/Scene comparison and
exact-main three-OS release. Keep issue1490 open until those gates pass.

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
wheel/smoke and materializer evidence are CI gates, not inferred from local tests.

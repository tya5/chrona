<!-- chrona:literal-acceptance/v1 -->

# Issue #1318 — temporary gate ref cleanup

Implementation: `d49846566edd3f203fb6d8a9a228b822cbaa4dcc`, prepared on
ready main `fed9727461e6fefa5b092cdea638bf3a722dfcef`.
[Current design, architecture and plan](https://github.com/tya5/chrona/issues/1318#issuecomment-6093049623).
WIP only; its PR waits for earlier M0/#1279 work. Do not close.

## Literal issue acceptance

### Issue #1318

- Source: [Issue #1318](https://github.com/tya5/chrona/issues/1318)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | After a sync completes, its gate branch is gone. The sweep removes a planted stale gate branch and leaves one whose run is in progress. | not met | [Mock-API planted stale/live sweep](../../../tests/unit/tools/test_derived_gate_cleanup.py) and [executed Bash/workflow safeguards](../../../tests/unit/tools/test_derived_gate_cleanup_workflow.py) pass. Normal published sync cleanup and live planted-ref evidence remain pending. | — |
| 2 | Do not edit `examples/**`. | met | [Owned implementation](https://github.com/tya5/chrona/commit/d49846566edd3f203fb6d8a9a228b822cbaa4dcc) changes tooling/workflow, contributor procedure and synthetic tests only. | — |

## Programme-level criteria (optional)

Focused helper/workflow/trusted-gate batch: 47 passed (11.70s). Real read-only
candidate inspection on ready `fed97274` returned `would-delete`; no ref changed.
Independent review found no unsafe deletion, gate weakening or ownership defect.
Unknown/active/incomplete evidence preserves refs; only 404 is idempotent.
Required release: fresh exact-head checks, normal sync cleanup/live evidence,
and exact-main three-OS conformance/pytest/wheel containing this review.

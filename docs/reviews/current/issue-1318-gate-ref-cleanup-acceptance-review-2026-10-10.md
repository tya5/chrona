<!-- chrona:literal-acceptance/v1 -->

# Issue #1318 — temporary gate ref cleanup

Implementation: `d49846566edd3f203fb6d8a9a228b822cbaa4dcc`; ordinarily adopted
ready main `14399aabc0daaf110a531a2dc21c5fa152aeb67c`
([trusted gate](https://github.com/tya5/chrona/actions/runs/38038775824)).
Owned helper/workflow/procedure/test bytes remain unchanged from the tested
`9a4510c8` checkpoint and public `0dab30ea`; the new main changes are outside
those files. No helper-focused rerun is needed for this adoption.
[Current design, architecture and plan](https://github.com/tya5/chrona/issues/1318#issuecomment-6093049623).
WIP only; its PR waits for earlier M0/#1279 work. Do not close.

## Literal issue acceptance

### Issue #1318

- Source: [Issue #1318](https://github.com/tya5/chrona/issues/1318)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | After a sync completes, its gate branch is gone. The sweep removes a planted stale gate branch and leaves one whose run is in progress. | not met | [Mock-API planted stale/live sweep](../../../tests/unit/tools/test_derived_gate_cleanup.py) and [executed Bash/workflow safeguards](../../../tests/unit/tools/test_derived_gate_cleanup_workflow.py) pass. Live candidate-policy checks deleted only the newly planted completed historical ref `e1a6f812` and kept active `0fd085d1` during [trusted run 38020103073](https://github.com/tya5/chrona/actions/runs/38020103073). These do not yet prove the published scheduled sweep or normal sync cleanup. | — |
| 2 | Do not edit `examples/**`. | met | [Owned implementation](https://github.com/tya5/chrona/commit/d49846566edd3f203fb6d8a9a228b822cbaa4dcc) changes tooling/workflow, contributor procedure and synthetic tests only. | — |

## Programme-level criteria (optional)

Current helper/workflow batch: 43 passed (12.29s); previous unchanged trusted-gate batch:
4 passed (0.03s). Real read-only
candidate inspection on ready `fed97274` returned `would-delete`; no ref changed.
Independent review found no unsafe deletion, gate weakening or ownership defect.
Unknown/active/incomplete evidence preserves refs; only 404 is idempotent.
Deletion assumes the existing immutable-candidate protocol: only `derived-sync`
publishes exact-SHA refs, and publication/sweep share one non-cancelling queue.
The API delete is not compare-and-swap; an external manual repoint between
recheck and delete violates that protocol and is not covered by these checks.
Required release: fresh exact-head checks, normal sync cleanup/live evidence,
and exact-main three-OS conformance/pytest/wheel containing this review.

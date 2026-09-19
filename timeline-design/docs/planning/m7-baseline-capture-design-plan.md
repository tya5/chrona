# M7 Baseline Capture Design Plan

**Status:** Complete — 2026-09-19

## Closed decisions

| Concern | Decision |
|---|---|
| Persisted output | One `snapshot-ref` resource at `snapshots/<snapshotId>.yaml`; it references Project bytes and never copies schedule or Scene data. |
| Identity | The reference records Project ID/kind/address, Store identity, exact opaque immutable revision, and SHA-256 content identity. |
| Atomicity | Compare the named Project base revision before publication; either the full readable snapshot resource exists or no resource exists. |
| Duplicate/stale failure | Existing ID, stale base, unavailable bytes, and identity mismatch reject without partial publication. |
| Undo/redo | Capture is non-reversible; later undo/redo cannot delete or retarget the immutable baseline. |
| Cross-store | Allowed only with independently pinned/verifiable Project and Snapshot Store references. |

## Implementation handoff

Implement a Revision Store capture adapter and command result that returns the created
`snapshot-ref` Resource Reference. Do not add Project mutation, scheduler output,
renderer state, Draft capture, or implicit baseline selection.

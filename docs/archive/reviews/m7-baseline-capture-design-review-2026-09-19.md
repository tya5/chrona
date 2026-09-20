# M7 Baseline Capture Design Review

**Date:** 2026-09-19  
**Disposition:** Pass — capture persistence and authority are closed for implementation.

| Review | Result |
|---|---|
| Command / Store ownership | Pass: Command Model owns intent; Revision Store owns CAS and immutable publication. |
| Resource form | Pass: existing `snapshot-ref` schema and canonical address supply the persisted result. |
| Atomic failure | Pass: no partial baseline on stale, duplicate, unavailable, or identity-mismatched input. |
| Authority | Pass: baseline refers to exact Project bytes and cannot include derived schedule or Scene data. |
| History | Pass: capture is intentionally non-reversible; no hidden deletion is introduced. |

The M7 baseline implementation may now proceed only through this contract.

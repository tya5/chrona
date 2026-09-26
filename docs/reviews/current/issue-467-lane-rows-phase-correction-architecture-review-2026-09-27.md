# Architecture Review — Lane Rows Phase and Version Correction (#467)

**Decision:** the correction lifts the recheck's hold. L1–L4 may proceed after L0 feasibility, following the [implementation amendment](../../planning/active/issue-467-lane-rows-implementation-amendment-2026-09-27.md). **Reviewed:** [phase and version correction](../../design/issue-467-lane-rows-phase-and-version-correction-2026-09-27.md).

| Concern | Authority | Result |
| --- | --- | --- |
| Phase order | #466 route-priority correction (phase contract; "required text in phase 1") | Consistent. Lane names are required, reserved text (`visible-overflow`; no suppression allowed by acceptance). Optional-label priority is unchanged for other modes. There is one obstacle index and no second collection. |
| Route quality | #466 route-priority correction, Specification 50 | Routes keep their declared limits; a lane name never moves to make room. Route suppression, if any, is diagnosed and attributed in L3 evidence. |
| View versioning | one live View version; schema inventory | The next free version at landing, copied from the live schema. |
| Row requirement | #480, Specification 24 §2.1 | Lane footprints extend the one `required_row_block_extents` path. |
| Group bands | #481 | Unaffected; lanes are group-local rows. |
| Table allocation | #487, ADR-0032 | The lane table uses the shared table measure. |
| Attached milestones | #486 | #486 consumes the allocator; no double ownership. |
| #488 | successor of #483 row 2 | Lane-local ladders satisfy row containment in lane mode; automatic mode remains #488's. |

**Risks:**
- **L0 feasibility.** The ≤12-lane threshold with required names may not hold on HALCYON `02`. The L0 gate stays a hard gate: if it fails, publish a design correction rather than weakening acceptance.
- **Route visibility.** Required names placed first may suppress some routes on dense slides. The L3 batch must list every route whose visibility changed.

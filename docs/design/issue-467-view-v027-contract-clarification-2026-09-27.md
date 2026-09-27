# Design Clarification — View v0.27 Lane Contract (#467)

**Clarifies:** the [selected lane design](issue-467-collision-aware-lane-rows-design-2026-09-26.md) and [phase/version correction](issue-467-lane-rows-phase-and-version-correction-2026-09-27.md). **Normative home:** [Specification 38 §3.1](../specification/38-review-row-composition.md). **Review:** [architecture review](../reviews/current/issue-467-view-v027-contract-architecture-review-2026-09-27.md). **Implementation:** [L2 amendment](../planning/active/issue-467-view-v027-contract-implementation-amendment-2026-09-27.md).

## Selected v0.27 grammar

- `rows.laneTable` is required with `rows.mode: lanes` and forbidden with `automatic` or `explicit`.
- `tableColumns` are item-subject declarations in the current View grammar. They have no lane or group subject, so all `tableColumns` are forbidden in lane mode; the separate finite `laneTable` provides only group/lane identity and optional item count.
- Lane mode requires plot labels containing `title` with `visible-overflow`. A migrated View that removes a visible delta column must include `finishDelta` in lane-label content to preserve that promise. This is a source-to-successor migration and acceptance gate, not a rule that every lane View universally display deltas.

These constraints do not alter `automatic` or `explicit` output, row ownership, routing priority, or issue acceptance. L2 keeps lane mode dormant and fail-closed until L3 supplies the Layout engine.

## Related records

- [Specification 38](../specification/38-review-row-composition.md)
- [Phase and version correction](issue-467-lane-rows-phase-and-version-correction-2026-09-27.md)
- [Architecture review](../reviews/current/issue-467-view-v027-contract-architecture-review-2026-09-27.md)
- [Implementation-plan amendment](../planning/active/issue-467-view-v027-contract-implementation-amendment-2026-09-27.md)

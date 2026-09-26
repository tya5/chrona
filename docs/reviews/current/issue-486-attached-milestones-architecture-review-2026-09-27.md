# Architecture Review — Attached Milestones (#486)

**Decision:** design approved. Data and automatic rows can land now; lane pinning lands after #467 L3. **Reviewed:** [#486 design](../../design/issue-486-attached-milestones-design-2026-09-27.md).

| Boundary | Result |
| --- | --- |
| Project / scheduling | `attachesTo` is metadata. The scheduler never reads it, and a schedule-equality test proves this. |
| Project schema | The field is added to v0.7 in place: it is optional and additive, and no document changes meaning. |
| Validation | The checks run after scheduling, because point and span are schedule results for `scheduled` forms. |
| View / Projection | Row membership is decided in Projection by reusing the existing `shared`-track fold. No new Layout concept is needed for automatic rows. |
| View schema | `attached` is a new `rows.points` value and the new default. It takes the next free View version, shared with #479 if they land together. |
| Layout / #467 | A pin is an input to the lane allocator, not a second allocator. |

**Risk:** the new default cannot change any existing render: no document carries `attachesTo` yet. The only behavioural change is for authors who add the field, which is the intent.

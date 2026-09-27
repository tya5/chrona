# Design — Attached Milestones (#486)

**Plan:** [design plan](../planning/active/issue-486-attached-milestones-design-plan-2026-09-27.md).

## Project data

1. **Field.** Project objects gain an optional `attachesTo: <object id>`, and scenario `objectOverride` gains `attachesTo: <id> | null`. The field is added to `project-v0.7` in place. It is optional and additive: every existing document stays valid, and the scheduler never reads it. This follows the repository's practice for Theme v0.11 and `presentation-preset-v0.1`.
2. **Meaning.** Attachment is presentation-relevant metadata, not a scheduling edge. Like `deadline` (Specification 05 §9), it never moves or constrains either object. `parent` stays independent, so a point may have a WBS parent and an attachment.
3. **Validation**, after scheduling (point-ness is known only then):
   - `E_PROJECT_ATTACH_TARGET_UNKNOWN`: the target does not exist;
   - `E_PROJECT_ATTACH_SELF`: the object attaches to itself;
   - `E_PROJECT_ATTACH_SOURCE_NOT_POINT`: the attached object is not scheduled as a point;
   - `E_PROJECT_ATTACH_TARGET_NOT_SPAN`: the target is not scheduled as a span (fixed, scheduled or rollup);
   - `W_PROJECT_ATTACHED_OUTSIDE_HOST`: a warning when the point's date falls outside its host's planned span.

## Presentation

4. **Rows policy.** `rows.points` gains `attached`, and an absent `points` now means `attached`. Under `attached`, a selected point whose host is selected moves onto the host's row as a `shared`-track member, exactly as the `predecessor` fold does today. Every other point keeps its own row. Existing data has no `attachesTo`, so `attached` is byte-identical to `own-row` for every committed slide. An explicit `own-row` restores a row per point, as the issue asks. `predecessor` applies attachment first and infers a host only for unattached points. `group-header` is unchanged.
5. **Visible facts.** An attached point's member label is required, not optional. Its text is the title, the planned date in the View's locale short form, and the finish delta when the point has one: `Campaign readiness review · 30 Sep · +2d`. The composition is fixed, and needs no new label vocabulary. The table keeps the host's columns.
6. **Lanes.** Under #467's `rows.mode: lanes`, an attached point is pinned to its host's lane before collision packing, the first placement rule named in #467's correction. Its label then follows #467's phase-1 required-text rules.
7. **Relations and annotations** anchored to an attached point resolve to its drawn mark, which Layout already does for shared-track members.

## Evidence

8. HALCYON-1's `campaign` (21 Sep to 8 Oct 2027) gains two attached gates inside its span: a readiness review and a range-safety review. Each HALCYON slide that selects `campaign` and uses automatic rows then shows them on the campaign row. Every changed slide is reviewed individually in the slice review.

## Boundaries

Core validation owns the field. Projection owns row membership. Layout only places members it is given, except for lanes, where the #467 allocator honours a pin. There is no Scene or adapter change, and scheduling is untouched.

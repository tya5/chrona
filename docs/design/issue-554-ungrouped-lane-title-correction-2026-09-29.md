# Issue #554 — Ungrouped multi-member lane title correction

**Corrects:** [lane presentation design](issue-554-lane-followups-design-2026-09-29.md). A valid generated lane may contain several members but have no Project group. The attached-milestones example has a campaign host with two attached gates and an empty group ID; requiring a group title rejects this valid render.

For a `lane` table label, use the sole member's Project title for a singleton. For a multi-member lane with a titled Project group, use the group title, appending the founder member title when multiple such lanes share that group. For an ungrouped multi-member lane, use its founder member's Project title as the human lane heading. The founder is the first member in the immutable lane membership projection; this changes only display text, never the lane key, grouping, count, or mark ownership. A missing usable Project member title remains a content diagnostic; never display a generated ID or explicit key as a fallback. An ungrouped `group` table label remains blank by declared group-presentation intent.

Add a regression using the public attached-milestones render and a focused table-content test. No View/Project schema, resource, Layout, Scene, or adapter change is needed. This rule deliberately narrows the prior design's assumption that every multi-member lane has a titled group.

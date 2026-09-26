# Design — as-of label placement closure (#458)

**Plan:** [design plan](../planning/active/issue-458-as-of-label-suppression-design-plan-2026-09-26.md).

The as-of label is timeline text with a stable `as-of-label` placement identity.
It follows the timeline's `visible-overflow` policy: Layout first seeks a
collision-free beside-line candidate; if none fits, the first beside-line
candidate is completed at its natural coordinate with a visible-overflow
warning. The label is not implicitly optional merely because other labels may
be author-suppressed.

A suppressed Layout text placement is a non-drawable disposition. Scene must
project only completed visible text; it may not treat the origin coordinates
of a suppressed record as geometry. This invariant applies to every text
family, not just as-of. Serialized Scene perceptibility checks the exact
`W_LAYOUT_LABEL_SUPPRESSED:<placement-id>` diagnostic identity against emitted
primitive IDs. A match is an error. The check has no source-specific allowlist
or numeric baseline. A generic origin ban is rejected: a valid slot can begin
at the origin and visible overflow can legitimately cross another slot's
boundary. Suppression identity is the structural evidence, while placement
coordinates are separately governed by Layout and slot policy.

Layout continues to own search, bounds and overflow facts; Scene only filters
the typed non-drawable disposition and projects visible placements. Adapters
remain unchanged. No schema version or author migration is needed. Existing
committed HALCYON 04 and 07 SVG/Scene bytes must change to place the label
beside its line; unexpected changes are a regression until reviewed.

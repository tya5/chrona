# Subtree Summary Completion — Implementation Amendment

**Amends:**
`issues-121-123-124-127-147-149-implementation-plan-2026-09-22.md` and
`issues-121-123-124-127-147-149-wbs-view-selection-implementation-amendment-2026-09-22.md`

**Design authority:**
`docs/reviews/current/issues-121-123-124-127-147-149-subtree-summary-completion-design-correction-2026-09-22.md`

## P4 refinement

Before completing P4, close `summary-profile-v0.2` so `scope: subtree` is
admitted only beside a typed `{object, facet: planned}` source.  In
`normalize_summary_content`, derive primary subtree membership solely from the
completed hierarchy `ReviewProjection`, de-duplicate comparison tracks, and
normalize the latest span-end / point-at date as the metric value.

Add direct fixtures for a mixed span/point subtree, nested selected roots,
comparison-track de-duplication, unselected root, non-hierarchy View,
non-primary root, and no known contribution.  Preserve every existing
unscoped metric result.  Then finish the already planned summary-bar
Layout-to-Scene projection, Theme binding, focused/materializer checks, and
the P4 full-suite/two-platform gate.

## Acceptance addition

P4 cannot close until its schema rejects scope on catalog or unsupported typed
sources, the normalized completion date is deterministic from View members,
and no summary, Layout, Scene, or renderer code reads raw Project hierarchy to
recover membership.

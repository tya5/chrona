# Design — Canonical Shared-Track Ordering and Summary-Bar Geometry (#417)

**Status:** Accepted for implementation.

## Ownership

Shared-track order is a finite semantic presentation policy, not paint
treatment.  The sole model-level function `shared_track_member_key(member,
source_index)` defines it as:

```text
snapshot, scenario, primary, actual, then any future/unknown source kind
```

It preserves the authored source index as the stable tie-breaker and leaves
non-shared members in their authored order.  Projection, Layout and Scene may
use this function to traverse an already-normalized row, but no layer may
restate the mapping.  Theme's `markPaintOrder` remains a completed visual paint
order: changing it must not change source traversal, placement identity or
accessibility order.

`summaryBar` is a semantic mark role.  Its block size is the positive
lane-relative `markHeight` token bound by the `summary-bar` Theme role and
resolved by `ThemeTokenView`; its block origin remains the completed row block
origin.  Summary bars do not receive mark offset, paint order, or corner-radius
semantics because they are rollup evidence rather than a member-track mark.

## Boundaries

View/Project establish member facts and authored source order.  The model owns
the closed semantic ordering policy.  Theme owns summary-bar size.  Layout
uses both inputs to create completed placements.  Scene only projects those
placements and may reuse the model key to preserve semantic traversal.  No
adapter reorders, measures, or derives geometry.

## Migration and acceptance

All shipped Themes bind `summary-bar.markHeight` to an explicit positive
number.  Tests must demonstrate a shared scenario's identical relative order
through every traversal, reject an invalid/missing summary-bar height, and
show that a changed token changes only the completed summary-bar geometry.
Public materializer evidence remains byte-characterized after regeneration.

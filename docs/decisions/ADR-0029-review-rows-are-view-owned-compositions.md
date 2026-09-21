# ADR-0029: Review rows are View-owned compositions

**Status:** Accepted — M28 design.

## Context

The former runtime derived exactly one `SceneRow` for every selected Project object.
That makes a row an accidental copy of a semantic object and prevents a review from
putting related tasks, milestones, and comparison facets on one visual line.

## Decision

A Review row is a stable View-local composition. It has a View-local ID, optional
label and group key, an ordered set of Review Items, and one table subject chosen from
those items. A Review Item has a stable View-local ID and an explicit source
`primary`, `snapshot`, or `actual` plus a stable Project-local object ID. Thus a
snapshot placement, an Actual observation, a span task, and a point milestone are all
ordinary review items. Row membership neither creates semantic containment nor changes
scheduling. The View owns row membership and order; the Layout Manifest owns row
geometry; Scene owns bounded track assignment and primitive coordinates.

View grouping belongs to the Review row, not to an item. A row may be grouped as an
owner/team/review section even when its items have distinct semantic owner fields.
Those owner fields remain Project facts and can be selected as table data; they do not
compete with the row's presentation group.

Automatic rows remain an explicit `rows.mode: automatic` composition: each selected
object produces its requested baseline and Actual review items in one row after the
View's existing selection/grouping/ordering pipeline. Explicit rows use
`rows.mode: explicit`; only their declared items are selected and their declared row
order is authoritative. A source/object pair may appear in more than one row.

## Consequences

Scene identity includes both row ID and Review Item ID. Table object-derived cells use
the row's table subject, while the row label supplies the title cell. Relations and
annotation anchors keep stable source/object IDs and resolve to the specific row/item
instance only when that target is unique; an ambiguous repeated item diagnoses.

This preserves Project, Snapshot, Actual, Theme, Layout Profile, and SVG boundaries.
It does not restore a Settings contract or introduce an authored-coordinate resource.

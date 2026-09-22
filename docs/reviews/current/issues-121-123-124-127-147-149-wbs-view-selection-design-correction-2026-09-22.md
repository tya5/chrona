# WBS View Selection and Summary Semantics — Design Correction

**Amends:**
`issues-121-123-124-127-147-149-design-review-2026-09-22.md`

## Trigger

P4 implementation discovery found four decisions not made by the published WBS
design: how a hierarchy selection predicate supplies expansion roots, what an
explicit parent row proves, what the `path` table source contains, and which
members a subtree summary aggregates.  Leaving them to projection code would
give View an implicit second hierarchy interpretation and make output depend on
accidental implementation order.

## View v0.3 hierarchy selection

In `grouping.by: hierarchy`, the existing `selection.include` predicate selects
**expansion roots**, not independently filtered rows.  A selected root emits
itself at relative depth zero and every Project descendant through the inclusive
`grouping.depth` limit; descendants need not separately satisfy the predicate.
When the predicate is omitted, all Project roots are expansion roots.  A root
that is also a descendant of another selected root is emitted once, below its
nearest selected ancestor.  A selected non-root object is valid and starts a
new relative-depth-zero subtree.

Project Core supplies normalized parent, canonical tree order, absolute depth,
display WBS code, and object-ID path.  View may apply its declared ordering only
within each sibling set, with object ID as a stable tie-break; it cannot create,
remove, or re-parent an edge.  `rollup` is attached only to a selected Project
rollup row and affects its presentation choice, not membership or placement.

## Explicit rows and table sources

Every explicit row has `depth >= 0`.  If `parentRow` is supplied, both rows'
table subjects must be primary Project objects and the child's Project parent
must equal the parent row's subject.  A root row cannot name `parentRow`; a
non-root row may omit it only when its hierarchy is intentionally not displayed
as an explicit tree.  This validates an asserted edge without making row order
or row depth a Project authority.

`wbsCode` resolves to the Project Core display code.  `path` resolves to the
ordered sequence of Project object titles from the selected object's Project
root through itself, joined with ` / `; it is a semantic string before Layout,
not a renderer-local breadcrumb.

## Subtree summary scope

A metric with `scope: subtree` names one selected primary Project object.  Its
member set is that object and its selected descendants, in View projection
order.  Snapshot/Actual comparison tracks for those members do not add new
members.  An unselected object, a non-primary source, or a non-hierarchy View
is rejected.  Summary code consumes the immutable View projection member set;
it never inspects Scene, table cells, or raw Project mappings.

## Whole-architecture review

The correction preserves the existing authority chain: Project Core determines
tree truth; View determines roots, expansion, ordering, and semantic table or
summary facts; Layout determines indentation and all geometry; Scene projects
completed placements; renderer adapters serialize primitives.  It adds no
compatibility parser or target-local WBS behavior.  P4.5 remains after P4,
where the finalized View vocabulary becomes named closure records.

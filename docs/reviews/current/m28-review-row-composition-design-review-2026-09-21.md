# M28 Review Row Composition Design Review — 2026-09-21

**Decision:** Design complete; implementation planning is authorized.

The review confirms that Review rows and Review Items belong in the View layer. A
Review Item has an explicit Primary, Snapshot, or Actual source and a stable object ID;
therefore tasks, milestones, snapshots, and observations are generalized rather than
special cased. Project objects keep semantic identity and scheduling meaning; the
Layout Manifest retains all concrete row geometry; and Scene alone creates item
subtracks and completed primitives. The table-subject and row-label rules prevent
ambiguous table values, while row/item projection IDs preserve reproducibility and
accessibility.

The review additionally confirms that grouping is a Review-row property. This keeps
owner/team review sections coherent even when one row contains items from different
semantic owners, and avoids an item-level grouping rule competing with row order.

Automatic rows are a named v0.2 mode, not a compatibility side path. Explicit rows
replace selection/grouping/ordering authority rather than combining with it. The design
therefore handles ordinary task/milestone co-location and later Actual overlays without
restoring deleted contracts or creating a parallel layout grammar.

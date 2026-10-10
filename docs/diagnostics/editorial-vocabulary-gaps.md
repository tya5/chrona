# Editorial: the reference elements chrona does not express (#383 row 4)

The Editorial appearance (bundled as the default, `chrona-default-draft`, and as the catalogue preset `editorial`) was built
from a designed reference slide. This report names every element of that reference that chrona cannot express yet, with
the role or capability it would need. It was missing when #383 closed (row 4); it is kept here, not in commit messages.

| # | Reference element | Status on main | Needs | Tracked in |
|---|---|---|---|---|
| 1 | Column headers set in upper case with tracking (`TASK`, `OWNER`) | not expressible: headers share the body `text` role | a Theme role for table column headers and the View member that selects it | #1373 row 1 |
| 2 | Owner column as initials | not expressible: the column shows the raw field value | a closed set of column cell transforms (initials first), applied by Layout | #1373 row 2 |
| 3 | A gate drawn inside its parent capsule | not expressible: a milestone is a free-row mark | a Layout placement rule hosting a point mark inside a span mark | #1373 row 3 |
| 4 | Legend milestone key without a spurious `W_LAYOUT_MARK_OVERFLOW` | resolved: the default render no longer emits it | nothing | |
| 5 | Reaching Editorial by name carries its legend | resolved: the `editorial` catalogue entry has a `detailProfile`, and `preset copy editorial` writes `detail.yaml` | nothing | |
| 6 | Rendering a Context straight from the bundled resources | not expressible: `LocalSnapshotReader` rejects a package-provider reference (`E_STORE_REFERENCE`), so the corpus keeps byte-identical copies under `examples/halcyon-1/` | a reader that resolves `provider: package` to the wheel resources | #1373 row 6 |

Not a gap: `progressFill` is exercised by the corpus (the bare default render draws `progress-fill:*`).

Related, delivered with #499: the legend keys of the bundled default now agree with the marks they name (a hollow milestone key, a
landscape capsule for a task duration, the coral fill in the Progress key, relation keys whose bounds enclose their points),
checked by `tests/support/legend_keys.py`.

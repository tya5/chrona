# Architecture Review — Table-Cell Semantic Purpose Correction (#402)

**Decision:** Accepted.

Scene purpose is not a paint alias.  The correction preserves the semantic
registry's one-binding authority, the public Scene table metadata invariant,
and Theme's independent role-binding responsibility.  Reusing existing finite
roles across distinct semantic identities is correct; reusing a plot-label
identity for a table primitive is not.

Implementation may resume only with the four table-cell identities and tests
that cover both unchanged plot-label purpose and table-row/column metadata.

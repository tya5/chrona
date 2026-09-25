# Implementation Plan Amendment — P1-I1 Contract Closure (#404, #403, #388, #389, #409)

**Applies to:** I1 of the published Table--Timeline Composition implementation plan.

Before I1 is accepted, implementation must:

1. express table widths with the corrected scalar/object logical-size grammar;
2. add `rowDecoration` and exclude it with other table--timeline declarations
   from dependency-network Views;
3. parse and retain `row_decoration`, `align`, `width`, and
   `hierarchy_column` in typed View input;
4. reject duplicate IDs and each hierarchy-column invariant at the typed
   contract boundary; and
5. migrate every corpus View and regenerate its public Scene evidence.

Focused evidence must include schema rejection for invalid width and
decoration forms, parser rejection for each hierarchy invariant, a valid
explicit nested-row fixture with a non-leading hierarchy column, inventory
validation, public materializer byte checks, and presentation-coverage
regeneration.  I2 may not rely on an implicit default for any v0.16 column
width or alignment.

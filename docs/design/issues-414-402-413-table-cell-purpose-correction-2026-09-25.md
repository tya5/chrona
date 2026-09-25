# Design Correction — Table-Cell Semantic Purpose (#402)

**Status:** Design correction complete; amends the semantic-to-visual
realization design and implementation plan.

## Trigger

I402-1 implementation exercised the completed Scene invariant: a primitive
with table-row/table-column metadata must have `purpose: table-cell`.  The
design's reuse of `varianceAhead`, `finishDelta`, and `varianceBehind` was
incorrect because those bindings intentionally have `purpose: finish-delta`
for plot labels.  Reusing a role name cannot change a binding's semantic
purpose.

## Correction

Create four table-cell-specific registry identities:

| Table fact state | semantic identity | Scene purpose | Scene role / Theme role |
| --- | --- | --- | --- |
| ahead | `tableVarianceAhead` | `table-cell` | `variance-ahead` |
| on-plan | `tableVarianceOnTrack` | `table-cell` | `variance-on-track` |
| behind | `tableVarianceBehind` | `table-cell` | `variance-behind` |
| missing observation | `missingActualCell` | `table-cell` | `missing-actual-cell` |

The first three reuse the existing finite paint roles but not the existing
plot-label semantic identities.  This preserves the distinction that a Scene
purpose expresses primitive meaning and metadata invariants, while a Theme role
expresses treatment.  Unknown finish variance and every unadmitted column
source remain `tableCell` with role `text`.

Layout continues to carry only the selected semantic identity on
`TextPlacement`; Scene looks it up and receives `table-cell` from the binding.
No Scene exception, placement-ID branch, or metadata relaxation is admitted.

## Acceptance amendment

I402-1 must prove that table primitives retain their required row/column
metadata for every state role, while plot-label `finish-delta` semantics retain
their existing purpose.  The realization report must distinguish the table
family's roles from plot-label evidence by primitive purpose.

# View v0.3 WBS Projection — Implementation Review

## Scope

Review P4 / issue #127: View v0.3 replacement, hierarchy projection, WBS table
facts, subtree planned-completion summary, and rollup summary-bar placement.

## Evidence

* View v0.1/v0.2 schemas and runtime mappings are removed; every live View is
  migrated to the single v0.3 schema.
* Focused contract, projection, summary, Layout, Scene, View-schema, and public
  materializer checks: **131 passed**.
* Complete suite: **297 passed, 4 skipped**.

## Boundary review

| Boundary | Evidence | Result |
| --- | --- | --- |
| Project Core → View | `normalize_hierarchy` supplies parent, order, WBS code and path; View only chooses expansion roots and sibling order. | Pass |
| View → summary | Scoped metrics consume `ReviewProjection` primary members and normalize the latest planned endpoint. | Pass |
| View/summary → Layout | Indentation, mark height, coordinates, and text bounds are calculated from measured sources by Layout. | Pass |
| Layout → Scene | Scene's structural test continues to reject measurement/routing imports; summary bar is projected from a completed shape. | Pass |
| Scene → renderer | The existing renderer resolves the emitted `summary-bar` Scene role through the declared Theme binding. | Pass |

## Intentional follow-up boundary

`SemanticBinding.theme_role` is not yet the renderer's resolved-role boundary;
the current renderer resolves Scene roles, as demonstrated by the established
`as-of` Theme bindings.  P4 therefore adds the required `summary-bar` binding
to live Themes without changing renderer policy.  P4.5 remains the planned
#147 representation-only closure point for named vocabulary records; it must
not alter P4's WBS semantics or output policy.

## Decision

P4 is ready for its implementation PR and two-platform publication gate.

# Issue 133 Critical-dependency Semantic-purpose Correction

## Trigger

The closed registry acceptance gate requires every semantic to have a unique Scene purpose. Issue 133 deliberately maps `dependency` and `dependency-critical` to one domain purpose (`dependency`) with distinct Scene and Theme roles. The implementation therefore correctly failed the existing gate rather than silently inventing a second domain relationship.

## Corrected invariant

`semantic_id` is unique. `purpose` identifies the semantic subject and may be shared by explicitly declared visual variants. The unique render-facing pair is `(purpose, scene_role)`; `theme_role` remains owned by the binding. The registry acceptance test changes from purpose uniqueness to pair uniqueness and adds an explicit assertion that the two dependency variants share purpose while retaining distinct roles.

## Architecture review

This preserves the Domain/Style distinction: criticality changes how an already-derived dependency is presented, not what relation exists in the Project. It keeps semantic registry authority central, prevents Scene from spelling a role literal, and does not introduce a new primitive or renderer branch. The correction is required before the v0.5 critical-relation surface can safely be implemented.

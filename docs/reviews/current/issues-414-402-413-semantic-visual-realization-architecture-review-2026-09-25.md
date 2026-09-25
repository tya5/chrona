# Architecture Review — Semantic-to-Visual Realization (#414, #402, #413)

**Decision:** Accepted, subject to the implementation constraints below.

| Boundary | Review result |
| --- | --- |
| Semantic authority | Pass. View source plus normalized Projection fact selects a finite semantic identity; no renderer, Theme predicate, or cell-string heuristic is introduced. |
| Layout / Scene boundary | Pass. Existing typed placement `semantic_id` is the correct completed handoff. Layout retains the choice with text/path geometry; Scene resolves registry bindings only. |
| Theme authority | Pass. Theme binds a declared role to treatment, but neither decides a fact state nor reads Project data. Purpose-specific bindings can intentionally share a treatment without deleting the distinction. |
| Marker and output boundary | Pass. `explanatory-arrow` uses the established completed `marker_end` geometry and target capability guard. SVG/PNG do not invent an arrowhead. |
| Route ownership | Pass. Annotation-specific finite Layout Profile limits avoid changing dependency routing behavior. Layout continues to compute and assess the completed path. |
| Evidence integrity | Pass. A generated registry/corpus/Scene report can measure realization without confusing adapter bytes or pixels with semantic evidence. |
| Compatibility and migration | Pass. One atomic migration of typed table cells, semantic registry, Themes, corpus, and generated artifacts is cleaner than preserving the old positional tuple as a parallel input. |

## Required implementation constraints

1. The realization-family registry is a finite, test-validated source of
   evidence policy.  It must not become a generic reflection of all Python
   model fields, an unbounded `when` language, or a reason to generate roles
   dynamically.
2. The normalizer must select a table-cell identity from the declared column
   source, not by searching `ReviewItem.roles`.  The only initial admitted
   state families are finish variance and missing observation, as specified in
   the design.
3. Every Layout-produced text that reaches Scene must carry an explicit
   semantic identity.  Scene must structurally reject a missing identity for
   table and annotation placements and must contain no branch on placement ID,
   annotation purpose, or table cell content for role selection.
4. `missingActualCell` is distinct from the existing mark semantic.  Its Theme
   binding and corpus evidence must demonstrate that it is readable as table
   text without changing mark geometry or treatment.
5. Annotation purpose must be preserved as typed Layout provenance.  Scene
   cannot recover it from an `annotation-*` source or relation identifier.
6. `explanatory-arrow` must carry completed marker geometry on the relation
   placement and pass the existing target capability validation.  A target
   incapable of markers must fail according to the existing scene policy.
7. `annotationRouting` is consumed only for annotation leaders.  Tests must
   prove that changing it does not alter a dependency relation, and vice versa.
8. The report must label an intentionally shared Theme treatment separately
   from a missing Scene realization.  It may not mark a state covered merely
   because a role name appears elsewhere in a corpus Scene.

## Architecture conclusion

The design retains the repository's authority chain:

```text
Project facts -> View source / Projection -> normalized semantic intent
  -> Layout completed placement and path -> Scene registry projection
  -> target capability validation -> adapter serialization
```

It also follows the completed-Scene, portable-capability, Theme-binding, and
constraint-driven surface specifications.  No correction is needed before an
implementation plan is written, provided the constraints above are treated as
acceptance gates rather than documentation-only guidance.

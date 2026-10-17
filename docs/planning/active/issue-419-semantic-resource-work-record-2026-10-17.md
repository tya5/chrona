# Issue419 — semantic mapping resource

Status: design planning; no product implementation authorized before reviewer
review. Baseline: published main `aabc5e894af50555892c0007e48efb24c268f2f3`.
[Owner scope](https://github.com/tya5/chrona/issues/419#issuecomment-6234067417):
design record only, after issue1657 (implementation now published in PR1662).

## Published baseline and open questions

- `semantic_registry.py` has117 actual `_binding` declarations, not123; verify
  the complete inventory and all field consumers before choosing migration.
  The issue's older claim that primitive kind and Theme role are unread is not
  current: Scene kind checks and Layout/Theme resolution consume them.
- Spec49 owns the closed semantic→Theme→placement→Scene contract. Spec06/60
  expose one planned-mark colour encoding. Project `fields` and field roles
  already reach projection; issue344's typed declaration is future work.
- Determine the versioned resource boundary, names stable at RC versus internal
  factories, closed selectors over supplied facts, role-or-encoding outcomes,
  conflict diagnostics, scope-truthful legends, and source-derived coverage.
  Unknowns remain design questions, not facts implemented in code.

## Literal acceptance (parent remains open during design-only scope)

1. The semantic vocabulary is a versioned resource with a schema.
2. A design set can introduce a visual distinction the product did not anticipate, without a code change.
3. The presentation coverage report derives distinctions from resources rather than from source.
4. No field in the registry is unread.
5. The report lists every purpose drawn in the corpus with its realized role count, generated from committed Scenes.
6. Adding a purpose to the semantic registry without a classification fails the check.
7. The 31-of-40 figure, or its successor, is visible in a committed, checked document.

Rows5–7 are the consolidated issue433 acceptance, not optional follow-ups.
The current deliverable specifies how to achieve these; it does not mark them
implemented or close the parent.

## Design plan and publication boundary

1. Inventory all current bindings, grouped by mechanism; trace meaning, role,
   paint and every field consumer. Separate stale measurements from current facts.
2. Draft one versioned mapping resource/schema shape, YAML-addable distinctions
   and a closed predicate vocabulary combined with existing colour encoding.
3. Specify the single typed-field connection for issue344, RC public/internal
   contracts, conflict and missing-fact behavior, provenance and scoped legends.
4. Compare only needed lessons from official Vega-Lite encoding/conditions and
   design-token specifications; review whole-architecture ownership against
   Spec04/06/07/08/33/49/56/60/62 and adjacent designs.
5. Publish the selected design in a clearly non-normative Spec49 draft section;
   record migration and independently reviewable implementation slices here.
   No schema, runtime, examples or generated changes in this design publication.
6. Post one current Status linking the record and draft. Await reviewer before
   product implementation; unresolved design choices stay explicit.

Evidence: complete117-entry inventory; synthetic YAML use cases for role and
scoped encoding outcomes; literal acceptance→planned test/report mapping;
architecture consistency and migration review. Docs/literal checks apply to
this publication; future implementation uses focused tests and official
public-output/full release CI rather than an unneeded local full suite.

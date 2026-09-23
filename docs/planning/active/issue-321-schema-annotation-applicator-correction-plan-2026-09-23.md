# #321 Schema Annotation Applicator Correction Plan

## Verified discrepancy

The accepted completion-correction review claimed that the live-schema lint
traversed all reachable applicators.  Its `allOf` traversal instead descends
only into an immediate child containing `if`.  A structural `allOf` wrapper can
therefore hide nested conditionals and local `$ref` assertions from the lint.
Live `view-v0.8` and reference-constrained schemas demonstrate the gap.

## Corrected design

- Traverse every dictionary branch of `allOf`, recursively, exactly as for
  `oneOf` and `anyOf`.
- A structural composition carrier is traversed without duplicating all of its
  ordinary property annotations.  This narrow exemption applies only to the
  carrier itself; nested applicators and local reference constraints remain
  independently discoverable and checked.
- A branch containing only `$ref`, optional annotation metadata, and no local
  constraint is pure reuse and remains exempt.  Every other reachable branch
  is author-facing when its keywords make an author-selectable, omittable, or
  violable constraint.
- An `allOf` wrapper with a local assertion requires a description and a valid
  example.  Its contained local assertion also requires a description when it
  is an author-facing schema node.  Conditional forms keep one branch-level
  description/example rather than mechanically narrating their predicates and
  consequences independently.
- Examples are tested in their enclosing schema context.  No accepted input,
  resource schema, diagnostics reducer, or presentation boundary changes.

## Architecture review

This is a repository-quality gate operating only on author-facing schema
metadata.  It introduces no parsing fallback, second schema registry, or
dependency into Core, View, Layout, Scene, or renderers.  Inventory selection
remains the sole source of the live corpus.

## Completion evidence

The correction must add negative fixtures for a nested conditional and a local
`allOf` assertion, annotate each newly reachable live node, validate examples,
and pass conformance, structural gates, the full suite, public materializers,
generated-SVG comparison, and installed-wheel smoke before #321 closes again.

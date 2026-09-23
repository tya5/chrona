# #321 Completion Correction Plan

## Verified discrepancy

The first acceptance review verified the then-current gates, but those gates
were narrower than [Specification 56](../../specification/56-schema-authoring-and-diagnostics.md):

1. `SchemaViolation` omitted `resourceKind` and `resourceIdentity`.
2. The shared reducer was not used by operational, command, and authoring
   schema ingress.
3. Annotation traversal skipped conditional applicators and did not require
   examples for patterns, formats, or local reference assertions.

The closed issue is therefore reopened. No compatibility syntax or renderer
policy is introduced by this correction.

## Design decisions

- `SchemaViolation` receives nullable `resource_kind` and `resource_identity`.
  The helper accepts context explicitly; it does not inspect downstream typed
  contracts or infer an identity from invalid data.
- Every bytes-to-schema ingress calls the reducer and maps its result into its
  existing stable public error class/code. Success values remain unchanged.
- Annotation traversal follows schema applicators. Conditional constraints are
  documented where they are declared. Examples are required for unions,
  patterns, formats, conditionals, and local assertion wrappers, then validated
  against their enclosing schema context.
- No v0.5 parser, `fixed` alias, View/Layout/Scene import, or second contract
  registry is allowed.

## Completion evidence

The corrected implementation must prove context propagation at Core,
presentation-contract, operational, command, and authoring ingress; prove
annotation failures for a conditional and pattern lacking examples; pass every
live schema; and re-run conformance, structural gates, full pytest, public
materializers, generated SVG diff, wheel, and installed-wheel smoke.

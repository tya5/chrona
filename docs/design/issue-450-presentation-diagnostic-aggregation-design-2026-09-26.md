# Design — Presentation Diagnostic Aggregation (#450)

**Design plan:** `issue-450-presentation-diagnostic-aggregation-design-plan-2026-09-26.md`

## Decision

Presentation ingress gains a validation-only collection phase before it builds
any typed render closure.  The phase returns an ordered immutable sequence of
`PresentationDiagnostic` values:

```text
PresentationDiagnostic(code, resource_kind, resource_identity, pointer,
                       rule, message, phase)
```

`phase` is `schema`, `contract`, or `closure`.  Sorting is stable by declared
closure resource order, then RFC6901 pointer, rule rank, and message.  One
diagnostic remains byte-for-byte compatible at its existing CLI shape; two or
more are carried in the existing `diagnostics` collection, never concatenated
into one prose message.

## Validation phases

1. **Resource schema phase.** `explain_all_errors` maps every independent
   JSON-Schema leaf violation in one resource into ordered diagnostics.  Union
   wrappers are removed when their leaf explanations exist.  The current
   single `explain_errors` remains a compatibility helper implemented as the
   first member of this ordered result.
2. **Resource contract phase.** A resource with no schema errors is parsed and
   runs only semantic checks that depend on its schema-accepted shape.  A bad
   View therefore does not suppress an unrelated bad Theme or Layout Profile;
   it does suppress View hierarchy checks whose inputs are not trustworthy.
3. **Closure phase.** Once independently parsable resources are available,
   closure-only checks run in declared dependency order.  A missing/invalid
   prerequisite produces its own diagnostic and explicitly prevents only
   dependent checks.  Layout, Scene, and adapters never run if any aggregated
   ingress diagnostic exists.

## Scope and boundaries

The shared collector is used by explicit Draft resource files, immutable
Context/reference closure resolution, and preset/guided paths after each path
has established its resource declarations.  It does not turn unreadable files,
content-identity failures, or invalid Context envelopes into guessed resource
sets: those remain terminal boundary diagnostics because the independent set is
unknown.  Core scheduling diagnostics retain their existing list transport.

```text
source/resource declarations
      -> presentation collection (schema, contract, closure)
      -> typed closure OR ordered rejection
      -> Core schedule -> Layout -> Scene -> adapter
```

The collector owns no rendering policy, resource repair, schema mutation, or
fallback.  `parse_contract` remains the one typed-contract constructor and
cannot return partial contracts.

## Acceptance

- The issue's View+Theme three-error fixture returns three resource/pointer
  diagnostics in deterministic order in one Draft render invocation.
- Independent bad resources all report; dependent semantic validation never
  runs on an invalid raw value.
- One-error Draft and immutable callers retain their public diagnostic identity
  and wording.
- Valid public materializers, Scene bytes, and renderer paths are unchanged.

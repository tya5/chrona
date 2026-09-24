# Design Plan: Declared Vocabulary Integrity (#387)

**Status:** Proposed

## Purpose

Ensure that a value admitted by a published Chrona schema is either accepted
by the owning implementation or deliberately classified as open-ended.  The
work closes the five observed schema-to-render gaps without folding Theme,
annotation, locale, renderer, or Layout policy into one generic validator.

## Verified starting facts

1. Theme v0.5 admits scalar `marker` and `pattern` values, while the SVG
   adapter currently accepts only `triangle` and `outline`/`diagonal-hatch`.
2. Render Context v0.14 admits every non-empty locale string, while compact
   date formatting currently accepts only `en-US`.
3. View v0.12 declares relation, group, and temporal annotation anchors and
   makes `anchor.facet` and `anchor.endpoint` optional, while Layout currently
   implements only an object anchor with both values required.
4. `tools/diagnostic_inventory.py` inventories literal diagnostic construction
   and ingress reachability.  It intentionally does not inspect schemas or
   infer accepted domain values, so it must remain independent.
5. Issue #384 owns the decision to make marker/pattern geometry Theme- and
   Scene-owned.  Issue #386 owns annotation semantics and corpus evidence.

## Design questions and required decisions

1. Define a deterministic, generated inventory of declared closed and
   open-ended vocabularies, their owning implementation acceptance boundary,
   and the evidence used for each comparison.
2. Define an explicit reviewable exception form for values that are genuinely
   open-ended; an unconstrained schema must not silently evade the inventory.
3. Decide each of the five observed cases at its proper owner: narrow the
   declaration, implement the declared vocabulary, or declare a bounded
   open-ended contract with an owner-local validator.
4. Preserve the authority flow: schema/resource declaration -> owner-local
   normalization or validation -> Layout/Scene -> adapter.  Repository tools
   report divergence but never participate in product runtime.
5. Define diagnostics that name admissible values at the boundary that owns
   the vocabulary, without renderer-specific formatting or duplicate enums.

## Required architecture review

The design must review Core schemas, resource loading, Theme normalization,
Render Context normalization, View validation, Layout annotation resolution,
Scene completion, renderer adapters, diagnostic inventory, generated-doc
policy, and public materialization.  It must reject:

- a runtime dependency on a repository inventory;
- a global registry that takes ownership away from Theme, Context, or View;
- widening declarations merely to preserve historical permissiveness;
- adapter-only validation for values required before Scene construction; and
- a blanket allowlist with no field owner, reason, and expiry/disposition.

## Deliverables

- An English design that defines the declared-vocabulary inventory and the
  ownership decision for every observed divergence.
- A whole-architecture design review against #371 and the presentation
  pipeline.
- An implementation plan with independently publishable inventory, owner
  corrections, tests, generated evidence, and release-gate slices.

## Evidence required before implementation

- Locate every current product read/rejection site for the five values.
- Characterize valid and invalid resource loading/rendering behavior through
  public validation/render paths.
- Identify all schema paths that declare the values and all existing generated
  inventory conventions.
- Confirm whether current corpus resources rely on a value that the accepted
  design would remove or alter.

## Publication order

1. Publish this design plan.
2. Publish the accepted design and architecture review.
3. Publish the implementation plan.
4. Implement and publish each planned slice with focused tests.
5. Publish a release review after full tests, generated-report checks, public
   materializers, and three-platform CI; only then close #387.

# Implementation Plan — Bounded Theme Inheritance (#378 I378-2)

**Design:** `issue-378-bounded-theme-inheritance-design-2026-09-26.md`.

## T378-1 — Derived Theme contract and resolver

Add the v0.12 derived-Theme schema and a dedicated ingress resolver.  Define
the pinned relative base reference, canonical effective identity, whole-entry
`values`/`roles` replacement, and stable rejection diagnostics.  Do not alter
View, guided authoring, Layout, Scene, or adapter contracts.

**Acceptance:** valid five-line derived Theme resolves to an ordinary v0.11
Theme; unknown entry, traversal, identity mismatch, wrong base kind/version,
cycle, and invalid resolved effective Theme reject deterministically.

## T378-2 — Draft and immutable closure integration

Route Draft explicit/preset Theme inputs and immutable Context Theme references
through the same resolver.  Preserve effective Theme-only downstream closure
semantics and add provenance only outside Scene/materializer identity.

**Acceptance:** Draft and Context use equal effective Theme values/identity;
the renderer observes no derived representation; materializer closure remains
ordinary and pinned.

## T378-3 — Tutorial proof and release review

Add the compact base/derived Theme fixture, document the source form, and prove
two visible output differences.  Execute focused resolver/closure/render
tests, conformance and public materializer checks, review generated SVGs, and
publish an I378-2 acceptance review.

## Deferred boundary

View inheritance is not implemented by this plan.  A successor requires its
own field-by-field semantic audit and cannot share a generic merge helper.

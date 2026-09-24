# Design Plan: Endpoint Annotation Evidence (#386)

**Status:** Proposed

## Purpose

Complete the annotation feature as a truthful View-to-Layout capability: one
committed corpus slide must exercise an endpoint-anchored explanatory arrow,
and the declared anchor model must mean exactly what the product implements.

## Verified starting facts

1. #387 migrated View to v0.13: every View annotation now requires an object
   anchor, a planned/actual facet, and an endpoint.  The former relation,
   group, temporal, and optional-anchor claims are no longer published.
2. Layout resolves object endpoint bounds, projects annotation boxes in the
   annotations slot, and routes bounded deterministic orthogonal leaders.
3. No declared corpus View currently supplies a View-level annotation; the
   completed leader routing path has no public generated-SVG evidence.
4. Project v0.6 annotations are separate semantic notes.  They are normalized
   as note content, not used by the View annotation router.
5. #375 will measure the resulting annotation purpose/anchor coverage; #384
   owns marker geometry and must not be folded into annotation semantics.

## Design questions and required decisions

1. Define the Project-note versus View-callout relationship without allowing
   two declarations for the same positioned object.
2. Select a corpus scenario that requires a `finish` endpoint,
   `explanatory-arrow`, annotation-slot box, and route avoidance against at
   least one other annotation box.
3. Define the View/Theme/Layout resources necessary for that scenario without
   adding #384 marker geometry policy or #375 coverage-report policy.
4. Define characterization evidence for route determinism, endpoint binding,
   annotation purpose, source provenance, and public materializer bytes.
5. Review the result against Core/Project ownership, View selection, Layout
   geometry/routing, Scene primitive projection, Theme appearance, and SVG
   serialization.

## Required architecture constraints

- Project annotations remain semantic note facts; they must not acquire
  viewport coordinates, leader routes, or presentation-only placement.
- View annotations select and explain projected facts; Layout alone measures,
  allocates boxes, selects ports, and computes routes.
- Scene receives completed annotation box/text/leader placements; adapters do
  not measure text, choose endpoints, or route leaders.
- A corpus slide must use declared resources and the public materializer; no
  hand-authored SVG becomes evidence.

## Deliverables and publication order

1. Publish this plan.
2. Publish the English design and whole-architecture review.
3. Publish an implementation plan with separately reviewable contract,
   corpus-evidence, and release slices.
4. Implement according to that plan, with focused tests after each slice.
5. Publish generated evidence and release review after full verification and
   three-platform CI, then close #386.

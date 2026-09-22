# Issue 145 Dependency-Network Implementation Plan

## Preconditions

The Issue 145 Dependency-Network Design and Architecture Review is the
implementation authority.  In particular, no implementation may branch in
`render_review`, closure resolution, or a target renderer.  Layout owns all
network geometry; Scene dispatches only completed placement closure.

## Independent slices

1. **N145-1 — Surface contract migration and neutral dispatch.** Introduce
   View v0.8, Layout Profile v0.3, and Theme v0.3 typed/schema contracts;
   migrate all public materializable resources and compatible Profile
   requirements atomically.  Add explicit table-timeline surface intent,
   surface-specific slot validation, registry-backed `network` slot, Theme
   network tokens, and a Scene surface dispatcher whose table/timeline route
   reproduces existing bytes.  Verify schema/contract rejection of invalid
   field combinations, no `render_review`/closure/renderer change, public
   materializer byte checks, focused tests, and full pytest.
2. **N145-2 — Typed graph projection and Layout closure.** Derive typed
   `DependencyNetworkProjection` records from selected Project relations and
   Scheduler critical facts.  Implement the pure network Layout composer with
   deterministic longest-path ranks, View ordering, measured nodes/ports,
   orthogonal routes, suppression diagnostics, writing-mode transformation,
   and surface-quality invariants.  Verify determinism, cycle/end-point/
   routing failures, critical classification, collision/viewport properties,
   and full pytest.  No SVG serialization logic is added.
3. **N145-3 — Scene semantics and HALCYON release gate.** Add the network
   Scene adapter and registry semantics, without adding a primitive kind or a
   renderer branch.  Add a HALCYON dependency-network View/context/layout and
   generated SVG; verify node/edge/critical-edge identities, public
   materializer byte reproduction, generated SVG differences, output-property
   gate, focused tests, full pytest, and an architecture-boundary review.

## Publication and merge discipline

Each slice is a separate PR.  Before every merge, fetch `origin/main`, inspect
the exact commit range and merge state, require every CI check, and merge
serially without force push.  If a slice reveals a changed ownership boundary,
stop implementation, publish a design correction and a corresponding plan
amendment, obtain green CI/merge, then resume from the merged base.

## Issue acceptance mapping

| Requirement | Slice |
|---|---|
| explicit View surface and closed slot/profile contract | N145-1 |
| deterministic graph rank/order/routing and quality closure | N145-2 |
| registry-only semantic mapping to existing primitives | N145-3 |
| unchanged use case, closure, and renderer | N145-1 through N145-3 structural tests |
| one HALCYON context and common output-property gate | N145-3 |

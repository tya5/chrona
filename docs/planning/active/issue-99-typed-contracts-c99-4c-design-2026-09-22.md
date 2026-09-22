# Issue 99 Step 4 / C99-4C — Closure Consumer Completion Design

**Status:** Proposed design.  **Predecessors:** C99-4A PR #129 and C99-4B PR
#135.

## Problem

Although every closure resource now has an exact-schema typed contract, the
render use case retains a generic `_Closure.get(kind)`/`all_of(kind)` helper.
Projection and content public entry points also expose generic resource
mappings.  This permits new kind-string access to re-enter the pipeline and
weakens the closed contract boundary.

## Decision

`RenderClosure` is the sole closure-facing API outside closure resolution.
It exposes named accessors only.  The input-read ledger becomes an explicit
typed record owned by the use case; it is not implemented by generic resource
lookup.

The public projection/content entry points receive named contract types:

- projection: Project, View, optional Actual, and optional snapshot Project;
- content normalization: Project, View, optional Actual, Detail, and Summary.

At their domain boundary each function obtains the named frozen document/body
needed by existing semantic algorithms.  Internal helpers may operate on those
domain facts; no generic closure envelope or `ClosureResource` crosses the
boundary.  Summary remains a typed optional input but is only marked read when
the product path consumes it; current known-unused evidence remains unchanged.

## Structural evidence

Add source-structure tests that reject in product consumers:

- `ClosureResource` imports or `RenderClosure.resource(kind)` calls;
- kind-string generic getters/all-of helpers;
- `Mapping[str, Any]` / `dict[str, Any]` parameters representing closure
  resources on the projection/content public entry points.

Tests must also prove one typed closure produces the same SVG/read-input set,
and all five public materializers retain their bytes.

## Cross-design review

This completes the closure boundary before scheduling, Layout, Scene, and
rendering.  It neither moves geometry from Layout nor adds renderer policy,
protocols, schemas, or a product output target.  It strengthens Issue #99
Steps 1–3 without pre-empting Step 5 protocol design.

## Publication

Publish this design/review, then an implementation plan, then one implementation
PR with the full verification gate.  Step 5 starts only after C99-4C merges.

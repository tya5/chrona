# ADR-0026: Capture named baselines in an append-only immutable registry

**Status:** Accepted  
**Date:** 2026-09-21

## Context

A baseline must remain meaningful when branch names, working trees, and derived output
change. The prior in-memory capture helper demonstrates the semantic check but is not a
durable product boundary.

## Decision

A capture command verifies an immutable Project reference and creates exactly one
`snapshot-ref/v0.2` resource in a named append-only baseline registry. The resource
contains the Project reference only; it copies no schedule, Scene, or rendering.
Existing baseline IDs reject. Comparison resolves a baseline resource and a separately
verified candidate Project reference, potentially from different Stores.

## Consequences

- Baseline publication is durable, reviewable, and not retargetable by undo.
- A registry adapter needs atomic create-if-absent behavior.
- Comparison remains semantic and provenance-rich rather than a pixel-diff feature.

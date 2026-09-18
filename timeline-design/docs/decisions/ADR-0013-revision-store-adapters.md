# ADR-0013: Make Git a Revision Store adapter

**Status:** Accepted  
**Date:** 2026-09-18

## Context

Chrona's text-based canonical files should be pleasant to review in Git. Earlier
designs accidentally made full Git object IDs and repositories mandatory inputs to
rendering, commands, and federation. That would prevent a desktop GUI, local database,
or signed offline bundle from using the same core safely.

## Decision

Define a provider-neutral Revision Store protocol. Evaluation consumes immutable
snapshots and content identities; commands use a store-owned compare-and-set revision
token. Git implements this protocol but is not visible to core semantics or renderers.

## Consequences

- Git retains valuable capabilities: distributed history, branches, merge tooling, and
  line-oriented code review.
- Non-Git stores can support the same correctness invariants without pretending to
  expose commits or branches.
- Git-only v0.1 serialized contracts are retained for compatibility and superseded by
  versioned provider-neutral schemas.
- Implementations need adapter configuration and trust policy; this is deliberate
  rather than relying on ambient working-directory state.

## Alternatives considered

1. **Keep Git mandatory.** Simpler initially, but wrongly couples normal editing and
   rendering to repository availability.
2. **Use bare file paths only.** Easy to implement, but cannot guarantee reproducible
   multi-file evaluation or conflict-safe mutation.
3. **Make content hashes the sole revision identity.** Portable but insufficient for
   an atomic multi-resource snapshot and normal mutable-store concurrency.

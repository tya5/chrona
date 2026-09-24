# ADR-0023: Replace numeric layout authoring with one intent grammar

**Status:** Accepted

## Context

Chrona currently has two incomplete composition authorities: a prototype Layout Profile
and a complete Presentation Settings aggregate containing many layout numbers. The
prototype declares alignment that its solver does not consume, branches on region names,
and invents canvas/header/footer sizes. The aggregate is reproducible after resolution
but is too detailed for authors and encourages raw gaps, offsets, paddings, artificial
maximums, and whole-array replacement.

There are no external users whose files require compatibility. Keeping both paths would
make the cleaner design harder to understand and permanently preserve duplicate
authority.

## Decision

Replace both authoring paths with the single `chrona/layout-profile/v0.4` grammar owned
by Specification 33. It uses a stable-ID composition tree, intrinsic/fractional/bounded
sizing, logical two-axis alignment and distribution, Theme number-token distances, and
a bounded overlay anchor/guide/barrier model.

Complete Presentation Settings cease to be an authoring contract. Internal resolved
values may exist at module boundaries but cannot become a second persisted layout
resource. The implementation deletes the old schema behavior, lookup defaults,
compatibility fixtures, and runtime branches.

Do not introduce a general linear constraint solver. The closed grammar diagnoses
cycles and contradictions and has exactly one deterministic resolution order.

## Consequences

- Existing repository examples and tests are intentionally rewritten.
- No migration adapter or version switch remains in the runtime; v0.1 is deleted when
  v0.2 becomes reachable.
- Layout YAML becomes shorter and reacts to content, locale, metrics, and viewport.
- Theme is the reusable owner of concrete spacing values; Layout stores token names.
- View remains the owner of any data facet/repeat semantics.
- Relative placement is less expressive than Cassowary/Auto Layout but remains
  reviewable, deterministic, and sufficient for the accepted use cases.
- A future grammar extension requires a new use case and specification change; it may
  not reintroduce raw coordinate authority through an adapter.

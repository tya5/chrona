# #42 slide-grade vocabulary 実装計画（2026-09-21）

1. Extend View row item/schema and projection with `track`; compose shared-track marks with deterministic z-order.
2. Add Theme roles/metrics and Scene group-header/indented-table primitives, with required overflow checks.
3. Wire locale-aware axis label formatting, optional two-level bands, declared Actual cutoff/as-of primitive, and calendar-closure shading.
4. Admit Detail Profile legend entries and emit role-derived legend swatches.
5. Generalize mark-label visibility from explicit rows to automatic rows without duplicating table cells.
6. Add examples and focused unit/integration tests; regenerate committed SVG evidence through public materializer.
7. Publish implementation review after delegated pytest evidence is available.

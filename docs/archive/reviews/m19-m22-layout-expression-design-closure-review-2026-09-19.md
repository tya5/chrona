# M19–M22 Layout Expression Design Closure Review — 2026-09-19

**Disposition:** Pass — design complete; implementation authorized in dependency order.

| Gate | Integration result |
|---|---|
| M19 | `27`, schema, fixture, and ADR make Layout Profile the only composition authority; M15 profile is deprecated/migrated. |
| M20 | Solver, manifest, deterministic diagnostics, and target capability invariants are owned without copying View/Theme semantics. |
| M21 | Expressive primitives reuse Style roles and Theme tokens; no generated-image or preset branch enters the adapter. |
| M22 | AI/human resource proposals share validation, inheritance, accessibility, gallery, and release evidence. |

Cross-layer review passes: Project/Schedule/Actual remain immutable inputs; View facts are
not duplicated; Style/Theme do not become geometry owners; Scene coordinates remain
derived. The former M15–M18 implementation is explicitly a prototype and must migrate
before any layout-engine release can claim completion.

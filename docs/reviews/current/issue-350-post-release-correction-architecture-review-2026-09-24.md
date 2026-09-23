# #350 Post-release Correction Architecture Review

**Decision:** accepted for implementation.  The previous 2026-09-24 release
acceptance is superseded pending C350-1 through C350-5.

| Boundary | Decision | Review result |
| --- | --- | --- |
| Draft CLI -> Context | Exact v0.7 SVG/PNG profile is explicit input; catalog paths never imply a profile. | Preserves capability authority and rejection-only targets. |
| Iconify -> catalog | Importer resolves selected parents and aliases before serialization; the bundled variant also admits the terminal parent closure of its declared variant aliases. | Prevents dangling aliases and avoids a generic lossy suffix rule. |
| Catalog -> closure | Context remains the only resolver. Nearest-name diagnostics are computed from the closed catalog at closure, not Layout/Scene. | Preserves Layout and Scene isolation. |
| Normalizer -> external format | A pinned offline fixture is test evidence only; Node is not a runtime dependency. | Tests the hand-port without compromising offline Python operation. |
| SVG subset -> dependency | `picosvg` is deferred until an approved subset expansion. | Avoids expanding security/geometry authority merely to make rejection less inconvenient. |
| Public corpus -> release | Material evidence is a real closed catalog/materializer route. | Removes the synthetic-fixture substitution from the claimed default evidence. |
| Package catalog -> materializer | Explicit package resource references are identity-verified and copied into the immutable snapshot. | Avoids duplicating a bundled catalog while preserving reproducibility. |

The correction introduces no compatibility bridge and no adapter policy.  It is
consistent with Specification 64’s ownership: importer normalizes, closure
resolves, View selects, Layout places, Scene completes, and adapters serialize.

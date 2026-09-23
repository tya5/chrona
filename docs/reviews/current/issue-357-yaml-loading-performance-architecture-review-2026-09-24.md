# Issue #357 — YAML Loading Performance Architecture Review

**Decision:** accepted for implementation.

**Correction:** accepted after I357-1/2 profiling.  The bundled Material
catalog receives an identity-bound generated projection; all other catalogs
retain generic validation.  See
`issue-357-packaged-icon-projection-design-correction-2026-09-24.md`.

| Boundary | Decision | Review result |
| --- | --- | --- |
| Runtime layers -> YAML | A dependency-neutral codec is the sole production decoder. | Avoids Storage-to-Core/Presentation dependency inversion. |
| External resource -> decoder | Decode each read; do not cache. | Preserves revision-store and user-file freshness. |
| Packaged schema -> validator | Cache parsed packaged schemas and validator-owned registries. | Package resources are immutable for the process lifetime. |
| Codec -> safety | Select only `CSafeLoader` or `SafeLoader`. | Retains safe YAML semantics and fallback portability. |
| Performance -> acceptance | Test cache behavior by calls, record wall time outside CI. | Avoids flaky timing gates while retaining measurable accountability. |

The design preserves the one-way resource path: external resource ingress ->
typed validation -> closure -> Layout -> Scene -> adapter.  Performance cache
state neither resolves resources nor crosses that path.  No compatibility
reader or output-policy change is required.

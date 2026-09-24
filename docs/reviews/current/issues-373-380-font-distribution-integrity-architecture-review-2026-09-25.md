# Architecture Review: Font Distribution Integrity (#373, #380)

**Decision:** Accept design.

| Boundary | Decision | Result |
| --- | --- | --- |
| Resource data → FontMetrics | The substitute descriptor names the fallback; FontMetrics only resolves declared data. | Preserved |
| Metric measurement → target output | Target-neutral substitutions are projected by RenderReview after target completion. | Preserved |
| Primary package → optional provider | An unpublished provider is not advertised as an installable root extra; CI retains explicit provider evidence. | Preserved |
| Wheel policy → runtime | Size checking is a build/release gate, not a package-discovery or rendering rule. | Preserved |
| Upstream font source → provider artifact | An explicit offline build tool copies the matching notice and produces pinned generated artifacts. | Preserved |
| Provider closure → Layout/Scene/adapters | Provider assets remain resolver inputs; only metrics reach Layout, completed placements reach Scene, and declared bytes reach raster adapters. | Preserved |
| Materialization → Japanese corpus | Context and SVG regenerate through the existing public materializer; no manual evidence mutation. | Preserved |

The design corrects a data-leak and a distribution defect without creating a
second font-selection authority.  In particular, `drawn` is an output fact,
not a measurement property: projecting it in RenderReview avoids a target
branch in Layout or Scene and avoids an adapter-owned diagnostic API.

Removing the unresolved extra is intentionally a clean correction rather than
a compatibility shim.  The local provider remains an explicit CI/development
dependency, so optionality changes failure behavior only where the provider is
absent; it does not lower the supported CJK contract.

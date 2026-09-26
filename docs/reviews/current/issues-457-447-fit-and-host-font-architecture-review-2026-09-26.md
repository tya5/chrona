# Architecture Review — Fit Completion and Host Fonts (#457, #447)

**Decision:** approved for implementation planning against the [design](../../design/issues-457-447-fit-and-host-font-design-2026-09-26.md).

| Boundary | Consistency finding |
| --- | --- |
| ADR-0031, Specifications 08/33/50 | The #449 no-fit-refusal rule includes `solve_layout`, not only surface composition. Normal-flow warnings flow to one completed Layout result; no adapter expands output. |
| View / Layout Profile | Valid authored overflow and thinning choices remain explicit. `strict` placement cannot override the higher-level valid-closure production guarantee. Invalid references and profile contradictions unrelated to fit still reject. |
| Theme / font closure / Layout | Exact package-or-declared faces are reused; only missing pairs invoke the volatile host bridge. Selected collection face determines metrics before Layout. |
| Scene / SVG / PNG | Scene projects completed warnings and text face identity. PNG may load the collection file but may not select a different family/weight or substitute a host font. |
| Immutable Context | It can render the same Layout fit fallback deterministically. It cannot depend on a host font bridge or path. |
| Existing #411/#448 design | The change repairs host discovery and extends the draft catalog without weakening exact matching or multi-face measurement. |

No example-specific override, implicit font substitution, synthetic weight,
or renderer-local canvas repair is accepted. Risks requiring verification are
very small viewports producing text before canvas origin, fontconfig family
aliases, and collection paint selection in resvg. Those risks are explicit
implementation gates, not assumed successful here.

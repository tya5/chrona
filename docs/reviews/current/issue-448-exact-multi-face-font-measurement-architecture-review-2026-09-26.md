# Architecture Review — Exact Multi-Face Font Measurement (#448)

**Design reviewed:**
`issue-448-exact-multi-face-font-measurement-design-2026-09-26.md`.

**Decision:** Accepted. The change removes an ingress-only capability
restriction by reusing the existing catalog boundary; it does not create a
second font-selection system.

| Boundary | Review result |
| --- | --- |
| Theme closure → draft font resolution | The resolved Theme is the single source of requested finite face pairs. Resolution occurs once before Layout and remains exact. |
| Font resolution → Layout | Both immutable and draft rendering provide the same selector-shaped metric catalog. Layout owns geometry and sees no host paths or font discovery. |
| Layout → Scene | A completed placement transports the identity of the selected metric; Scene only projects it. No Theme or font lookup moves into Scene. |
| Scene → corpus audit | The audit consumes completed family, weight, and identity facts, then compares them against the immutable Context catalog. It does not infer a face from role names or rendered pixels. |
| Draft resolution → PNG | The renderer receives the complete closed tuple of identity-pinned files and remains unable to use host fallback fonts. |
| Immutable Context → all targets | The declared metric/font catalog remains the sole reproducible font closure. Draft host paths cannot cross into it. |

## Cross-cutting conclusions

The current `FontMetricsCatalog` already establishes the correct abstraction:
a treatment selects an exact face before measurement. Extending
`DraftFontResolution` to carry the same shape avoids a special regular-face
path and preserves the existing Layout and renderer ownership boundaries.

The new corpus audit is deliberately a release-evidence tool rather than a
second Layout validator. Layout proves selection while constructing placement;
the audit proves the committed serialized result still contains the exact
declared identity. This provides a structural regression detector without
binding renderers to metric internals.

Draft system font discovery remains a volatile ingress capability. Its inputs
are a fully resolved Theme and explicit opt-in; its output may contain host
paths only until target rasterization. This maintains the immutable
Context/snapshot portability model and keeps PDF/typeset exclusion intact.

No design correction is required before implementation.

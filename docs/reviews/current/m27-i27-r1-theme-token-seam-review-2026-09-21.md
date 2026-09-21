# M27 I27-R1 Theme Token and Scene Input Seam Review — 2026-09-21

**Decision:** Superseded by the measured-input correction review. The original
publication established the typed token API, but did not carry `MeasuredSources`.

I27-R1 adds a non-persistent `ThemeTokenView` over the already-resolved Theme
v0.2 closure.  It performs typed role/property lookup and emits stable diagnostics
for a missing role (`E_THEME_ROLE_REQUIRED`) or wrong token type
(`E_THEME_TOKEN_TYPE`).  It does not recreate an authoring token resource and does
not expose the deleted legacy `paints` or `strokes` shapes.

The v0.5 `SceneBuildInput` seam accepts only a `LayoutManifest`, normalized
`SurfaceContentInput`, resolved Theme v0.2, measured font input, and declared
capabilities.  It rejects an incomplete Layout Manifest before primitive construction
with `E_PRESENTATION_PRIMITIVE_MISSING`.  Core SceneSurface composition remains the
next, separately reviewed I27-R2 slice.

**Evidence:** `test_theme_tokens.py`, `test_v05_builder.py`, inherited surface-content
and closure tests, the full regression suite, and `conformance/run_conformance.py`.

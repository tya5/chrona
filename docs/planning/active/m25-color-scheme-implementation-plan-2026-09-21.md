# M25 Color Scheme Implementation Plan — 2026-09-21

**Status:** Approved design; implementation pending.

1. Replace Theme color-token loading with color-intent bindings and add the immutable
   Color Scheme loader, provenance checks, WCAG contrast checks, and stable category
   index function. Remove color-token and fallback paths.
2. Replace Render Context v0.4 loading with v0.5, require a Scheme reference, resolve a
   concrete Theme before Layout/Scene, and diagnose every missing or incompatible input.
3. Migrate fixtures and examples atomically; add positive/negative resolver and
   deterministic-order tests.
4. Add an explicit gallery command that evaluates separate closed Contexts, not adapter
   overrides. Verify output has unchanged geometry and non-color cues across schemes.
5. Run the full test/conformance suite and publish final acceptance evidence.

Each item is a separate GitHub-published phase. Any design mismatch returns to
Specification 34 and this plan before code continues.

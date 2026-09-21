# M25 Color Scheme Implementation Plan — 2026-09-21

**Status:** Complete.

1. Complete a source-path inventory of every paint resolver, literal fallback, and
   renderer color default; publish the deletion/replacement matrix and negative tests.
2. Replace Theme color-token loading with color-intent bindings and add the immutable
   Color Scheme loader, provenance checks, WCAG contrast checks, and stable category
   index function. Remove color-token and fallback paths.
3. Replace Render Context v0.4 loading with v0.5, require a Scheme reference, resolve a
   concrete Theme before Layout/Scene, and diagnose every missing or incompatible input.
4. Migrate fixtures and examples atomically; add positive/negative resolver and
   deterministic-order tests.
5. Add an explicit gallery command that evaluates separate closed Contexts, not adapter
   overrides. It preflights all closures, rejects duplicate Scheme content identities,
   sorts by Scheme identity, and writes an ordered manifest. Verify output has unchanged
   geometry and non-color cues across schemes.
6. Run the full test/conformance suite and publish final acceptance evidence.

Each item is a separate GitHub-published phase. Any design mismatch returns to
Specification 34 and this plan before code continues.

# Implementation Plan — Presentation Diagnostic Aggregation (#450)

**Design:** `issue-450-presentation-diagnostic-aggregation-design-2026-09-26.md`  
**Architecture review:**
`issue-450-presentation-diagnostic-aggregation-architecture-review-2026-09-26.md`

## I450-1 — Ordered schema explanation

Add `explain_all_errors` and focused schema fixtures for leaf/wrapper removal,
stable multi-error ordering, and preserved first-error compatibility.  Do not
change closure traversal yet.

## I450-2 — Resource collection boundary

Introduce typed presentation diagnostics and a validation-only collector for
the known Draft resource set.  It validates every independent resource,
parses only schema-clean values, and records dependency suppression explicitly.
Add the three-error View/Theme fixture plus one dependent semantic fixture.

## I450-3 — Closure and CLI transport

Use the collector from Draft, immutable Context, preset, and guided ingress
once declarations are known.  Introduce an ordered aggregate rejection at the
render boundary and serialize its diagnostics through the existing CLI result
list.  Preserve one-error public output.

## I450-4 — Release evidence

Run focused schema/closure/CLI tests, public materializer reproduction, and
structural import checks.  Regenerate diagnostics documentation only if stable
identifiers change.  Use one three-platform CI run for full suite/wheel gate;
inspect that no generated Scene/SVG changes occur for valid corpus inputs.

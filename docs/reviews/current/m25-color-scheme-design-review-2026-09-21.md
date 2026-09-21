# M25 Color Scheme Whole-Design Review — 2026-09-21

**Decision:** Implementation authorized.

## Boundary audit

| Boundary | Decision | Evidence |
|---|---|---|
| Style → Theme | Style still returns roles, never colors. | Specification 34 §1 |
| Theme → Scheme | Every paint binding names a closed Scheme intent. | Specification 34 §3; ADR-0022 |
| Scheme → Context | Context holds the selected immutable Scheme reference. | render-context v0.5 schema |
| Context → Scene | Resolver emits a concrete Theme before measurement. | Specification 34 §4 |
| Scene → Output | Output receives resolved paint only. | Specification 34 §4 |

There is no fallback palette, inherited scheme, renderer-local selection, or Theme-local
literal color path in the target design. Existing literal-color Themes are replacement
inputs, not compatibility resources.

## Risk closure

- Category assignment is hash-based and independent of group ordering.
- Text contrast against both declared surfaces is validated before Scene emission.
- `suitability` is declarative; markers, patterns, and text alternatives remain
  mandatory independent semantic cues.
- Built-ins require explicit provenance and license metadata; no external bytes are
  admitted in M25 without redistribution evidence.

The D2 schema fixtures validate one positive Scheme and one missing-license rejection.
The main Chrona conformance suite remains passing. No unresolved product-design decision
blocks implementation.

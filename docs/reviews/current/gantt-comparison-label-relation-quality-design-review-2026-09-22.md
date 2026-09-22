# Gantt Comparison Label and Relation Quality — Design Review

**Decision:** I58-3 implementation is authorized after this review is published.
**Scope:** label overflow and relation quality from Specification 50 §3.2–§3.3.

## Cross-layer consistency

| Layer | Responsibility | Explicit non-responsibility |
| --- | --- | --- |
| Project | relation facts and endpoints | visual route geometry |
| View | label/relation intent and overflow choice | coordinates and pixel thresholds |
| Layout Profile | route bend and detour limits | relation selection or SVG semantics |
| Ingress normalizer | one canonical form for legacy aliases | geometry policy |
| Layout | candidate measurement, collision checks, routing, scoring, suppression | SVG serialization |
| Scene | semantic primitive projection | fallback selection, measuring, routing |
| Materializer | byte/PNG evidence | policy repair or example branching |

## Review findings

The existing `labels` and `relations` forms do not express the required failure
behavior.  Their normalization must occur once before Layout; neither Scene nor
the renderer may interpret an alias.  Label candidate ordering and relation score
tie-breaking are deterministic Layout algorithms.  HALCYON selects public policy
declarations only; it does not introduce coordinates or identifier branches.

## Decision constraints

- A suppressed label/relation remains a typed placement with a stable diagnostic.
- Required text, marks, accepted labels, and timeline bounds are protected geometry.
- `finishDelta` has one representation when selected as a plot label.
- A route must satisfy bend and detour limits, not merely be geometrically connected.
- Any newly discovered cross-layer owner returns implementation to this review.

# Issue 99 Step 4 — Typed Closure Contracts Design Review

**Decision:** Approved for implementation planning in three atomic slices,
starting with C99-4A.

## Evidence reviewed

- `presentation/model/closure.py` validates the render context but releases
  generic YAML dictionaries through `ClosureResource.value`.
- `usecases/render_review.py`, `presentation/model/projection.py`, and
  `presentation/review/v05_content.py` consume and reinterpret those mappings.
- Exact current schemas exist for every resource in the review closure, while
  `presentation-resource-v0.1.schema.yaml` is deliberately only a generic
  envelope, not an acceptance schema for a concrete resource.
- The current source direction and the completed product seam are protected by
  #113, #114, and Specification 08.

## Findings

1. A generic envelope is the wrong runtime type.  It couples every consumer to
   serialized field names and permits accidental mutation after validation.
2. Letting contract parsers become a second acceptance authority would fork
   diagnostics and make schema evolution unsafe.  Exact schemas must accept or
   reject first; contracts merely make accepted data immutable and explicit.
3. A broad rewrite of every domain payload is unnecessary and risky.  Frozen
   named payload fields give a real boundary now without moving scheduler or
   presentation policy into the closure layer.
4. The render pipeline needs a single typed closure, but the renderer must not
   learn resource contracts.  Its input remains SceneSurface.

## Cross-design consistency

| Existing design authority | Review result |
| --- | --- |
| Issue 94 / Specification 08 product seam | Preserved: contracts terminate before Layout; Scene and renderer retain their completed boundary. |
| Issue 58 layout foundation | Preserved: no geometry, measurement, route, or text-placement logic is introduced outside Layout. |
| Issue 99 Steps 1–3 | Strengthened: the use case becomes the sole closure consumer, import direction remains inward, and the vocabulary registry stays the sole semantic authority. |
| Closure integrity reviews | Strengthened: resource identity is frozen together with typed accepted facts; snapshots retain their project identity check. |
| Public materializer contract | Preserved: no declaration, target, command, or expected SVG policy changes. |

## Risks and controls

| Risk | Control |
| --- | --- |
| Contract conversion changes rendered output | keep each C99-4 slice byte-characterized across all public materializers; no artifact update is permitted. |
| Schema and parser drift | central exact-schema registry, schema-first test, and no parser-owned defaults. |
| Accidental mutable payload | recursive freezing at construction and an attempted-mutation test. |
| Coupling optional profiles to mandatory path | C99-4B is separate and retains absent-profile behaviour exactly. |
| Architectural overreach | structural tests prohibit generic closure resource mappings in completed consumers; Step 5 protocols remain out of scope. |

## Exit decision

The design has a single acceptance authority, explicit runtime ownership, and
bounded migration slices.  C99-4A may now receive an implementation plan; no
implementation changes are approved by this review itself.

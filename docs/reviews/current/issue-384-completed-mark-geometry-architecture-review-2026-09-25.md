# Issue 384 — Completed Mark Geometry Architecture Review

**Status:** accepted  
**Reviewed design:** `issue-384-completed-mark-geometry-design-2026-09-25.md`  
**Date:** 2026-09-25

## Review result

The completed-mark geometry design is consistent with the current presentation
architecture, subject to the implementation gates below.  It removes a real
adapter ownership violation without moving geometry selection into Layout or
semantic policy into Theme.

| Architecture concern | Evidence and decision | Result |
|---|---|---|
| Project / View authority | The design adds no Project fields, View selector, annotation semantics, or route intent. | Pass |
| Semantic registry | Existing `planned`/`actual`/`snapshot` bindings remain the only semantic source; Theme role `milestoneSymbol` is appearance-only. #385's unrelated literal roles remain explicitly deferred. | Pass |
| Theme / Scheme split | Theme supplies finite shape/tile dimensions; Scheme continues to supply paint colour. No geometry contains a colour or a Scheme intent. | Pass |
| Layout / Scene seam | Layout supplies final bounds and routes; Scene expands only Theme-selected appearance into completed primitive geometry. It cannot alter feasibility or placement. | Pass |
| Renderer neutrality | Scene carries path/tile/dimension data and not marker names. SVG target syntax is confined to SVG. SVG-derived PNG/PDF consume the same Scene. | Pass |
| Capability honesty | Required geometry is checked before adapter output. Typeset adapters cannot preserve their current partial/comment-only result. | Pass |
| Closed vocabulary | Schema `oneOf` and finite shapes reject unsupported authored choices at load. No free path/SVG namespace is introduced. | Pass |
| #385 readiness | Immutable dataclasses and closed values are serializable in a subsequent explicit Scene schema. This design does not prematurely define that public schema. | Pass |
| #375 / #383 boundaries | The design supplies a general hatch mechanism but does not decide a dot-grid vocabulary, an editorial preset, or corpus measurement policy. | Pass |
| Migration integrity | All live Theme resources and generated evidence migrate atomically; obsolete runtime readers are forbidden. | Pass |

## Findings carried into the implementation plan

1. The current `PaintFamily` decision reads a pattern string before completing
   paint.  Replace that with typed Theme treatment resolution so an outline
   treatment becomes completed no-fill paint and hatch receives an explicit
   payload.
2. `PathCommand` has no SVG-only close instruction.  Closed outlines must use
   explicit final line segments, preserving adapter-neutral vocabulary.
3. Existing Render Context visual profiles cover SVG/PNG only; direct typeset
   adapters still need explicit surface capability validation at their entry
   point, rather than a speculative expansion of Context target contracts.
4. The public materializers have byte-characterization checks.  Preserve the
   existing corpus geometry exactly for migrated default tokens, regenerate all
   committed SVG evidence once, and review only intentional changes.
5. Do not combine the `variance-*` and literal `planned` semantic-registry
   repairs with this work.  They are #385 Phase 0 and would obscure the
   geometry-boundary acceptance evidence.

## Acceptance gate for implementation planning

The implementation plan must divide work into independently publishable slices
for: Scene data/type completion; Theme v0.7 and resource migration; SVG and
typeset capability behavior; tests and public materializer evidence.  Each
slice must name focused tests, a full-suite gate, generated-diff review, and
the exact condition that permits #385 to begin.

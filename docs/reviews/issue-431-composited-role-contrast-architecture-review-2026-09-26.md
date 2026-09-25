# Architecture Review — Composited Role Contrast and Corpus Visibility (#431)

**Design reviewed:**
`issue-431-composited-role-contrast-design-2026-09-26.md`.
**Decision:** Accepted for implementation planning.

## Boundary review

| Boundary | Decision | Result |
| --- | --- | --- |
| Semantic registry → Theme closure | Finite role classes and finite state-text treatment select a fixed floor. | Accepted; no colour-name or primitive-id heuristic. |
| Theme → Layout | `none` is a typed decoration disposition, so Layout does not create a drawable placement. | Accepted; no transparent shape workaround. |
| Layout → Scene | Scene transports explicit absent decoration evidence and completed enabled primitive paint. | Accepted; omission is observable without an adapter branch. |
| Scene → quality evaluator | Shared pure compositing uses only completed hex paint, opacity, and canvas ground. | Accepted; no rasterizer, font, or geometry repair. |
| Scene → adapter | Adapter receives only enabled primitives and serializes supplied paint. | Accepted; it cannot choose a floor or hide a failed decoration. |
| Report → CI | The checked report is derived from committed Scenes and emits every finding. | Accepted; no baseline allowance or one-error reduction. |

## Required implementation controls

1. `contrastTreatment` is required and validated only for classified state
   text roles; it cannot become an unbounded role property or numeric floor.
2. `backgroundTreatment: none` is accepted only for classified decoration
   roles.  A missing paint binding for an enabled role remains an ingress
   error, not implicit absence.
3. `decorationDispositions` must be schema-validated, deterministic, and
   derived from the resolved Theme before adapter invocation.  It records
   absence independently of whether a particular surface has geometry for an
   enabled decoration.
4. The shared composition kernel is the only implementation of sRGB
   linearization, alpha compositing, and contrast.  Existing perceptibility
   observations must be refactored to call it before #431 policy code is
   added.
5. The initial policy rejects only flat classified paints against opaque canvas
   ground.  A classified gradient, shadow, or variable host cannot quietly
   bypass the floor; it is a named diagnostic until a richer ground model is
   designed.
6. Theme migration, regenerated public Scenes/SVGs, contrast report, diagnostic
   inventory, and materializer proof are one release unit.  Palette-only
   publication is not accepted.

## Whole-architecture consistency

The design preserves #400/#449's distinction between invalid input and
completed visible fit outcomes: unreadable state paint is rejected at Theme
closure, while a completed decorative visibility failure is observed and
reported from its Scene.  It preserves #446 as the owner of generic Scene
observation while making #431 the owner of thresholds and class policy.  It
does not move paint, formatting, or visibility decisions into a renderer.

# Implementation Plan — Surface-Aware Contrast (#459)

**Base:** `0a1b2c770dfabc31452d639300ad5009dc5328a2`.
**Design:** [selected contract](../../design/issue-459-surface-aware-contrast-design-2026-09-26.md),
[architecture review](../../reviews/current/issue-459-surface-contrast-architecture-review-2026-09-26.md),
[mark-role correction](../../design/issue-459-mark-role-normalization-correction-2026-09-26.md),
[painted-sample correction](../../design/issue-459-painted-sample-and-hosted-mark-correction-2026-09-26.md).
[Opaque-gradient correction](../../design/issue-459-opaque-gradient-ground-correction-2026-09-26.md)
is also normative for this slice.

## Literal acceptance gates

1. `variance-behind` text is held to 4.5:1 and meets it on every committed slide.
2. Mark roles have a floor, and every committed planned bar meets it against the surface it is drawn on.
3. The contrast report states, for each primitive, the ground it was measured against.

## Slices and publication

1. **Policy kernel and report.** Extend `semantic_registry.py`,
   `scene/contrast_policy.py`, `scene/paint_analysis.py` if required, and
   `tools/presentation_contrast.py`. Tests in
   `tests/unit/chrona/presentation/scene/test_contrast_policy.py` and
   `tests/unit/tools/test_presentation_contrast.py` cover overlapping
   paint-order Rects, canvas fallback, opaque linear-gradient sample points,
   painted-edge stroke-only Rects, hosted
   progress fills, and per-primitive
   ground evidence. Publish with no corpus gate enabled until the atomic
   resource migration below is ready; do not leave a public red main.
2. **Atomic policy/resource migration.** Change all affected Theme
   `variance-behind` treatments and Scheme amber/mark colours, including
   controller-z, HALCYON, orion and every other affected public variant.
   Inspect the elevated gradient host in actual SVG as well as flat surfaces.
   The probe's 954 initial failures are a resource-audit worklist, not a
   baseline to suppress. Regenerate
   `docs/diagnostics/presentation-contrast.md` and all affected public
   Scene/SVG materializer outputs in the same publication unit. Verify every
   classified finding and inspect generated SVG in one batch, paying special
   attention to `09-gallery-mono` planned bars and actual painted fills.
3. **Release review.** Run focused tests and conformance locally; use CI for
   full three-OS pytest, public materializers, newest-Python reproduction and
   wheel/smoke. Record exact commit, generated diff, CI link, architecture
   observations and each literal criterion in
   `docs/reviews/current/issue-459-surface-contrast-acceptance-review-2026-09-26.md`.

The first two steps may be one atomic product commit if the new checker makes
the old corpus fail. Each published commit must remain materializable.

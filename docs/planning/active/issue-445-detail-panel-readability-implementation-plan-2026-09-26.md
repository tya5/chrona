# Implementation Plan — Detail-Panel Readability (#445)

**Design:** `issue-445-detail-panel-readability-design-2026-09-26.md`  
**Architecture review:** `issue-445-detail-panel-readability-architecture-review-2026-09-26.md`  
**Entry condition:** the design and review are published; implementation must
not start if their Layout ownership boundary changes.

## I445-1 — Completed panel-block composition

**Files:** `src/chrona/presentation/layout/surface_composer.py`, with a small
private helper colocated with slot/text composition; `surface_quality.py` only
if an invariant needs a typed, reusable helper.

1. Extract the current `group-details` and `milestones` branch from the
   generic one-line side-content loop.
2. Build each entry through measured `wrap_text` and `place_text`, preserving
   existing formatting, source identity, typography selection and visual
   target identities.
3. Complete final per-panel `SlotPlacement` bounds from the measured text
   block; allocate overlapping panel inline intervals by stable vertical
   stacking.
4. Add panel containment/non-intersection checks before `SurfacePlacement`
   validation.  Do not add a Scene, renderer, or Review Detail resolver
   fallback.

**Acceptance:** Japanese group detail has multiple deterministic CJK lines;
text bounds are inside final panel slots under normal wrapping; group detail
and milestone text do not intersect; all prior group/milestone semantic IDs
and selected font facts remain present.

## I445-2 — Explicit completed overflow record

**Files:** the same Layout composition helper and existing `FitWarning`
construction path; focused Layout/Scene tests.

1. For a final detail panel beyond the requested viewport, expand the
   completed canvas through the existing `_completed_canvas` route and append
   a deterministic `W_LAYOUT_VISIBLE_OVERFLOW` / `detail-panel` record.
2. Apply a declared exceptional slot disposition to an unbreakable oversized
   unit; do not invent a renderer-specific alternative or resurrect
   `diagnose`.
3. Verify the Scene builder and serializers retain final slot bounds, lines,
   warning payload and canvas verbatim.  No Scene code should be modified
   unless the test identifies an actual projection loss.

**Acceptance:** the long Japanese panel completes successfully with a larger
canvas and structured warning when appropriate; an intentional overlap fixture
stacks deterministically; SVG text uses supplied `<tspan>` lines; no adapter
imports Layout text measurement/wrapping.

## I445-3 — Corpus evidence and focused verification

**Files:** Controller-Z Japanese and every affected public materializer output
under `examples/**/generated/`, plus generated diagnostic/coverage documents
only where source closure changes them.

1. Regenerate every public materializer after all source changes are complete
in one batch.  Do not hand-edit generated Scene/SVG evidence.
2. Inspect Controller-Z Japanese executive Scene geometry and an SVG/raster
render; inspect the other side-panel contexts enumerated by #445 for
unexpected canvas or line-break regressions.
3. Run focused Layout text/composer, Scene projection, renderer ordering, and
public-materializer reproduction tests.  Run schema/inventory gates only if
their affected generated output changes.
4. Review generated diffs, `git diff --check`, import-direction/Scene-delivery
structural checks, then publish the one atomic implementation commit.

**Release acceptance:** defer the full suite to the existing three-OS CI and
newest-Python public-materializer jobs.  Query CI only after this material
implementation publication, and batch P0 #439/#443/#435/#445 release review
against that evidence.  Do not perform repeated local full-suite runs or CI
polling.

## Non-goals and stop conditions

- Do not generalize to every text slot, redesign the Layout Profile language,
  or implement #446's generic Scene evaluator in this slice.
- Do not alter #435 boolean presentation, #439/#443 paint strata, or existing
  source ordering/semantics.
- If measured panel allocation requires a new cross-layer data type, a
  renderer decision, or an undeclared overflow policy, stop implementation,
  publish a design correction and architecture review, then amend this plan
  before resuming.

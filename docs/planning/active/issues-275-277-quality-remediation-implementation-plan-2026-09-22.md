# Issues 275–277 Quality Remediation Implementation Plan

## Preconditions

This plan follows the merged remediation design and the Theme-metric correction.
Each slice is independently reviewed, verified, and merged. No slice adds scheduler
policy to View, coordinate policy to Scene, or renderer-local fallback behavior.

## P275 — Driving critical relations

1. Extend `ScheduleAnalysis` in `src/chrona/scheduling/scheduler.py` with a
   deterministic relation-identity set. Derive it after successful placement from
   source endpoint, lag/calendar, and target endpoint equality; retain ordinary
   critical-object analysis for its existing consumers.
2. Carry that analysis evidence through `build_review_projection` in
   `src/chrona/presentation/model/projection.py` as an immutable review fact.
3. Make `normalize_v05_surface_content` select `relations: critical` only from that
   fact, preserving the selected relation's semantic role and never reconstructing a
   chain from endpoint criticality.
4. Add scheduler cases for zero-lag, positive lag, working-calendar lag, and a
   zero-float non-driving relation; add projection/review characterization for the
   latter. Run focused tests, full pytest, materializer byte checks, and SVG diff.

Acceptance: every emitted critical relation is driving; every driving selected
relation is emitted deterministically; existing non-critical relation modes retain
their behavior.

## P276a — View-dependent Theme metric requirement

1. Add a normalized View-to-metric-requirement function at the presentation request
   boundary. Header grouping adds `timeline.groupHeader.blockSize`; non-header Views
   add nothing.
2. Let `resolve_theme_metrics`/`measure_sources` validate that explicit requirement
   set and issue `E_THEME_METRIC_REQUIRED` at the Theme metric pointer before a
   `MeasuredSources` value exists.
3. Remove the missing-metric fallback/classification from `surface_composer`; retain
   only geometric overflow validation there.
4. Test header missing metric, non-header reuse of the same Theme, a declared metric
   that cannot fit, public materializers, generated SVG, and full pytest.

Acceptance: missing binding is a Theme diagnostic; positive declared values are
consumed by Layout; only actual allocated-capacity failure reports a Layout overflow.

## P276b — Project object-type selection

1. Extend `schemas/view-v0.8.schema.yaml` and the typed View contract so geometry
   kind (`span`/`point`) remains its current selector while Project object-type
   include/exclude is expressed independently.
2. Normalize and apply the predicates once in `projection.py`, before hierarchy
   expansion, grouping, ordering, row construction, and dependency-network selection.
3. Add schema, contract, and projection tests for type inclusion, exclusion,
   geometry-kind intersection, explicit rows, and hierarchy roots. Regenerate only
   affected public evidence and run full pytest.

Acceptance: a View can select Project types independently of schedule geometry;
legacy geometry declarations preserve their meaning; all downstream surfaces consume
the same selected object set.

## P277 — Two-level calendar axis geometry

1. Extend the typed Layout placement closure with coarse-band rectangles and a
   per-level grid classification. Compute both from configured axis levels, including
   centred coarse labels only when their measured text fits their own interval.
2. Give grid paths plot-only extents from the timeline slot's top through its bottom;
   distinguish coarse major from fine minor semantic roles in Layout-owned placement.
3. Reduce `v05_builder` to projection of those completed shape/text placements and
   update semantic bindings only as required for the existing Theme roles.
4. Add two-level axis placement, centring, fitting, grid-extent, and Scene projection
   tests. Validate generated SVG hierarchy, public materializer bytes, and full pytest.

Acceptance: two-level axes have non-overlapping typed lanes, visually coherent bands,
and grid hierarchy without Scene coordinate or fitting decisions.

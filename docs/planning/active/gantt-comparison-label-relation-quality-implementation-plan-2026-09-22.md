# Gantt Comparison Label and Relation Quality — I58-3 Implementation Plan

**Status:** Design correction and implementation plan.  I58-3 begins after
I58-2 merge `c4639ec`.

## Correction

The current View schema has plot label placement but no overflow declaration, and
relations are a string without a quality policy.  The router proves only that a path
exists.  None of these is sufficient for Specification 50 §3.2–§3.3.

## Normalized contract

At ingress, labels normalize to placement, content, side, and `overflow` (`suppress`
or `diagnose`).  Legacy booleans retain their documented existing behavior.  Relations
normalize `semantic` to `{mode: semantic, overflow: diagnose}`; `none` remains none.
Layout Profile owns `relationRouting.maxBends` and `maxDetourRatio`.

## Atomic implementation unit

1. Extend schemas and one ingress normalizer; do not inspect aliases in Layout/Scene.
2. Layout ranks deterministic label candidates against marks, accepted labels, required
   text, and timeline bounds; it returns a fitted placement or explicit suppression /
   diagnostic. `finishDelta` is emitted once.
3. Layout scores relation candidates by crossings, Manhattan length, bends, then points;
   it applies configured quality limits and returns a suppression warning or diagnosis.
4. Add neutral label and relation fixtures covering acceptance, suppression, and failure.
5. Adapt every affected HALCYON View/Layout declaration and regenerate evidence in the
   same PR only after focused tests, full pytest, materializer, and PNG review pass.

## Acceptance

A58-03, A58-04, and A58-06 require placement-level tests.  Scene only projects accepted
placements; it cannot choose fallback labels or routes.  This plan is published before
implementation and is followed by a separate implementation PR.

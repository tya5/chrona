# Issue 133 Critical-path and Total-float Design Plan

## Purpose

Define a scheduler-owned critical-path analysis that reaches the review surface
without giving View, Layout, Scene, or a renderer scheduling authority.

## Verified starting point

* The reference scheduler resolves only earliest placements.  Its public port
  currently reduces `ScheduleResult` to `ScheduleOutcome(placements,
  diagnostics)`, so adding fields to the private result alone cannot reach a
  `ReviewItem`.
* Project v0.3 already permits object `deadline` and end `constraints.max`.
  Specification 04 and Project-format specification 05 explicitly say that a
  deadline is an evaluative target, **not** a scheduling bound.
* The semantic registry declares `dependency`, but not the spec-authorized
  `dependency-critical`; View v0.4 has no `critical` relation mode and table
  vocabulary has no `totalFloat` source.

## Design questions to settle before implementation

1. Reconcile Issue #133's proposed deadline-based backward-pass target with
   the normative deadline/constraint separation.  The default candidate is
   the maximum resolved terminal endpoint; a deadline may affect criticality
   only after an explicit specification amendment authorizes it as an analysis
   target without making it a placement bound.
2. Define a single `ScheduleAnalysis` value carried by both `ScheduleResult`
   and public `ScheduleOutcome`: per-object early/latest endpoint evidence,
   integer total float in that object's calendar, critical membership, and the
   selected analysis target/provenance.  No separate presentation calculation
   is permitted.
3. Specify backward propagation for point, fixed span, scheduled span, rollup,
   end-max constraints, relation endpoint pairs and negative/calendar lag.
   Unsupported cyclic or partially invalid graphs retain their current
   diagnostics and expose no partial analysis.
4. Define how a selected View occurrence inherits analysis from its Project
   object, how Snapshot comparisons remain isolated, and whether rollups are
   visual critical members or only derived envelopes.
5. Define the closed presentation extension: `critical` item role,
   `totalFloat` table source and `signedDays` formatting, `critical` relation
   visibility, registry binding and Theme requirement for
   `dependency-critical`.

## Required architecture review

The resulting design must prove this unidirectional path:

```
Project + calendars + relations -> Scheduler analysis -> ScheduleOutcome
    -> ReviewProjection -> normalized presentation -> Layout route choice
    -> Scene primitive role -> renderer bytes
```

It must also prove the negative boundaries: Project authors do not tag an item
critical; View does not recompute float; Layout does not select a critical
path; Scene does not infer criticality from geometry; renderers only serialize
the selected semantic role.

## Planned deliverables and gates

1. Publish a design review resolving the target policy and all temporal edge
   cases above, including an explicit consistency review against specifications
   02, 04, 05, 07 and 12.
2. Publish a separate implementation plan with independently reviewable
   scheduler, contract/projection, and presentation/materializer slices.
3. Only then implement with three-path calendar fixtures, fixed/constraint
   boundary cases, cycle/no-partial-analysis cases, projection/role/column
   tests, relation filtering tests, public materializer characterization and
   generated SVG review.

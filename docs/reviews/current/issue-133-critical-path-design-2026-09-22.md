# Issue 133 Critical-path and Total-float Design

## Decision

Criticality is a derived scheduler analysis, not Project authoring or a presentation heuristic. A successful schedule produces one immutable `ScheduleAnalysis` with per-object latest placements, integer total float, critical membership, and provenance-bearing component targets. `ScheduleResult` and public `ScheduleOutcome` carry the same value. An invalid or unsupported schedule has no analysis rather than a partial critical path.

## Analysis target and deadline policy

For each weak dependency component, backward analysis ends at that component's latest resolved `end` or `at`. A singleton has itself as target; therefore a Project without relations has every object critical. Rollup envelopes create no independent target.

Deadline is excluded from backward placement analysis. Scheduling Model §10, Project Format §9, and Q-SCHED-2 require that it remain an evaluation target rather than a scheduling constraint. A later feature may expose deadline status, but it is not float. An explicit `constraints.end.max` is a late-end bound and caps latest placement; infeasibility retains existing diagnostics.

## Backward pass

The current forward pass is the sole source of earliest placements. For every acyclic component, the scheduler derives each latest endpoint from its component target, fixed placement, own max constraint, and successor endpoint bounds. It mirrors forward relation arithmetic with `retreat`/`advance` and the identical lag/calendar selection. Points use `at`; spans preserve declared amount; fixed placements are immovable; rollups have no independent float or critical membership.

`total_float` is the number of forward calendar steps from early to latest start/at in the object's own calendar. `wd` uses its working calendar; calendar-day amounts use Date steps. Negative float is a diagnostic, never a derived value, and suppresses the whole analysis.

## Projection and presentation

`ReviewItem` gains `total_float` and `critical`. Primary items receive current analysis; Snapshot items receive separately scheduled Snapshot analysis. Style adds a `critical` role as a fact, never as an override. View adds `totalFloat` table source and `critical` relation mode. Such a relation is selected only when both resolved primary endpoints are critical. The registry maps `dependency-critical` to dependency purpose, critical Scene role, and the same Theme role. Layout still owns routing; renderer only serializes the selected role.

## Architecture consistency review

This follows Domain Model §13 and Style/Theme §4.3 while preserving deadline/constraint separation:

```
Project graph -> Scheduler analysis -> ScheduleOutcome -> Projection -> View
normalization -> Layout route -> Scene role -> renderer
```

No author tag, View rule, Layout result, Scene geometry, or renderer fallback can create criticality.

## Acceptance evidence

Three-path, work-calendar, fixed, end-max, singleton, rollup, invalid/cycle, projection/Snapshot, View/schema, registry/Theme, Scene, materializer, and generated-SVG tests prove the result end to end.

# Update a plan after a week of work

A plan changes while the work happens. This guide is the loop for keeping one plan file
current: record what happened, move the as-of date, re-plan what is left, and draw the
result next to the plan you started from. It uses plain files: no Store and no saved
Context. The same loop keeps [`examples/chrona-roadmap`](../../examples/chrona-roadmap/README.md)
current.

1. Keep a copy of the plan as the baseline.
2. Record the actuals.
3. Move `asOf`.
4. Change the plan dates.
5. Render with `--actual` and `--snapshot`, and read the picture.

## 1. Keep the baseline

Save the baseline by copying the plan file. This is the whole mechanism for a draft:
`render --snapshot <the saved project.yaml>` compares the current plan with that copy, with no
Store, no command file and no identity pin. Do not edit the copy afterwards:

```bash
cp project.yaml baseline.yaml
```

(`chrona baseline-capture` is a different thing: it saves a named baseline into a Store from a
command document, which is the pinned path for reviewed history, not needed here.)

This guide's files are `update-baseline.yaml` (the plan as first agreed, 2026-11-02 to
2026-12-01), `update-plan.yaml` (the plan after the update) and `update-actual.yaml`.
The baseline:

<!-- chrona:doc-check file: update-baseline.yaml -->
```yaml
version: timeline/v0.7
project: {id: website, title: Website relaunch}
objects:
  design: {type: task, title: Design, schedule: {mode: fixed-span, start: '2026-11-02', end: '2026-11-09'}}
  build: {type: task, title: Build, schedule: {mode: fixed-span, start: '2026-11-09', end: '2026-12-01'}}
  launch: {type: gate, title: Launch, schedule: {mode: fixed-point, at: '2026-12-01'}}
relations: []
```

## 2. Record the actuals and 3. move `asOf`

`actual.yaml` holds one observation per object. After two weeks, Design is done and Build
has started:

<!-- chrona:doc-check file: update-actual.yaml -->
```yaml
version: chrona/actual-set/v0.3
kind: actual-set
id: website-observed
body:
  asOf: '2026-11-16'
  observations:
    - {id: design-1, sequence: 1, projectObjectId: design, actual: {start: '2026-11-02', finish: '2026-11-12', progress: 1}}
    - {id: build-1, sequence: 1, projectObjectId: build, actual: {start: '2026-11-12', openUntil: asOf, progress: 0.2}}
```

- `start` is the first day worked.
- `finish` is the day **after** the last day worked, like a plan `end`. Design was worked
  through Wednesday 2026-11-11, so its `finish` is `2026-11-12`.
- A task still open has a `start`, no `finish`, `openUntil: asOf` and a `progress` below 1.
  Without `openUntil` the observation is incomplete and its bar is not drawn
  (`W_LAYOUT_ACTUAL_INCOMPLETE`).
- A gate that has happened takes `at` instead of `start` and `finish`.
- `asOf` is the date the observations are true on. Move it forward each time you update; it
  draws the TODAY marker.
- To correct an observation, add one with a higher `sequence` for the same object: the
  highest `sequence` wins.

## 4. Change the plan dates

Design ran three days longer than planned, so what is left moves. Change the dates in
`project.yaml` itself (here, Build starts on 2026-11-12 and the launch gate moves to
2026-12-08). Leave the work already done as it was planned, so it shows as late:

<!-- chrona:doc-check file: update-plan.yaml -->
```yaml
version: timeline/v0.7
project: {id: website, title: Website relaunch}
objects:
  design: {type: task, title: Design, schedule: {mode: fixed-span, start: '2026-11-02', end: '2026-11-09'}}
  build: {type: task, title: Build, schedule: {mode: fixed-span, start: '2026-11-12', end: '2026-12-08'}}
  launch: {type: gate, title: Launch, schedule: {mode: fixed-point, at: '2026-12-08'}}
relations: []
```

If your tasks are `scheduled` (an `amount` such as `15wd`, placed by its relations), change
the amount or the relation instead and read the new dates from `chrona schedule`; do not
compute them by hand. Check the edited plan:

```bash
chrona validate update-plan.yaml
chrona schedule update-plan.yaml
```

## 5. Render and read it

Pass the edited plan, the actuals and the baseline. The `target-b` preset draws the
baseline and the `Δ finish` column. The default preset accepts `--snapshot` but draws no
baseline; `render` says so with a `W_SNAPSHOT_NOT_DRAWN` warning (status stays `ok`), so name
a preset that draws one:

```bash
chrona render update-plan.yaml --actual update-actual.yaml --snapshot update-baseline.yaml \
  --preset target-b --output update-after.svg
```

Reading `update-after.svg`:

- **Dashed outline (ghost):** where the baseline had the task or gate. Build and Launch show
  a ghost left of their current bar: they moved by the update. Design has no ghost, because
  its plan did not change.
- **Solid bar:** the current plan. **Dark line:** the actual. A striped bar is a task open
  at `asOf`.
- **`Δ finish`:** the Actual finish minus the **current** plan's finish, in calendar days.
  Design reads `+3d` (it finished 2026-11-12 against a planned 2026-11-09). Build reads a dash
  because it has no finish yet. Moving the plan to match an actual makes its delta `+0d`, so
  the ghost, not the delta, shows how far the plan moved.

`render` refuses to replace an existing output file; choose a new name for each update, for
example `plan-2026-11-16.svg`. Warnings (`W_...`) arrive as JSON lines on standard error with
exit 0; [the diagnostics reference](../../skills/chrona/references/diagnostics.md) says what
each means.

## The next update, a week later

Compare with the same baseline again, or copy the current plan over the baseline to compare
with the plan as it now stands. Then:

1. **Record next week's actuals by adding to `actual.yaml`; do not rewrite it.** Keep the earlier
   observations and append new ones for the same objects with a higher `sequence`: the
   highest `sequence` of an object wins, and the older lines remain as the record. Close Build and
   record the gate, then move `asOf`:

<!-- chrona:doc-check file: update-actual-week2.yaml -->
```yaml
version: chrona/actual-set/v0.3
kind: actual-set
id: website-observed
body:
  asOf: '2026-11-23'
  observations:
    - {id: design-1, sequence: 1, projectObjectId: design, actual: {start: '2026-11-02', finish: '2026-11-12', progress: 1}}
    - {id: build-1, sequence: 1, projectObjectId: build, actual: {start: '2026-11-12', openUntil: asOf, progress: 0.2}}
    - {id: build-2, sequence: 2, projectObjectId: build, actual: {start: '2026-11-12', openUntil: asOf, progress: 0.55}}
```

2. Change the plan dates if what is left moved, then render again under a new output name:

```bash
chrona render update-plan.yaml --actual update-actual-week2.yaml --snapshot update-baseline.yaml \
  --preset target-b --output update-after-week2.svg
```

What the draft path offers for writing actuals: edit or append to `actual.yaml` as above, or keep
the observations as columns (`progress`, `actual_start`, `actual_finish`) of the sheet you
[import](csv-import.md) with `chrona import --actual-output` (it never replaces a file, so write a
new one). There is no draft command that records an observation for you. `chrona actual-intake` does
that for a Store, from an intake batch command document (schema `actual-intake-batch`) and a
Store config; there is no step-by-step guide for it yet, so it is a known gap.

An AI coding agent finds the same loop in the [chrona agent skill](../../skills/chrona/SKILL.md#update-the-plan-after-a-week-of-work).
Reading a plan from a Store or a saved Render Context is a different path; see the
[progressive Project tutorial](progressive-project-tutorial.md).

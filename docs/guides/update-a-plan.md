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
  support: {type: task, title: Post-launch support, schedule: {mode: fixed-span, start: '2026-12-29', end: '2027-01-08'}}
relations:
  - {id: design-to-build, type: dependency, from: {object: design, endpoint: end}, to: {object: build, endpoint: start}, lag: 0d}
  - {id: launch-to-support, type: dependency, from: {object: launch, endpoint: at}, to: {object: support, endpoint: start}, lag: 0d}
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
- An open task is drawn from its `start` up to `asOf`, and `finish` is the day after the last day worked, so a
  task whose `start` is the `asOf` date itself has no extent yet: no bar is drawn and `render` warns
  `W_LAYOUT_OPEN_ACTUAL_INVALID` (status stays `ok`). The bar appears at the next update, when `asOf` is later than
  the `start`; to draw it now, move `asOf` to the next day.
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
  support: {type: task, title: Post-launch support, schedule: {mode: fixed-span, start: '2027-01-05', end: '2027-01-15'}}
relations:
  - {id: design-to-build, type: dependency, from: {object: design, endpoint: end}, to: {object: build, endpoint: start}, lag: 0d}
  - {id: launch-to-support, type: dependency, from: {object: launch, endpoint: at}, to: {object: support, endpoint: start}, lag: 0d}
annotations:
  design-late: {kind: note, text: Copy arrived two days late, anchor: {object: design}}
  vendor-risk: {kind: risk, text: Vendor review may move the launch gate, anchor: {object: build}}
```

**Notes and risks** are the top-level `annotations` map of the plan, as in the block above: a `kind` (`note` or `risk`),
one short `text` and an `anchor: {object: ID}` naming the task or gate. You never place them on the picture; the
design draws each one, in the plot or its notes rail as the design lays it out. A note or risk that the design's View
has no binding for is not dropped silently: `render` names it in a
`W_PRESENTATION_ANNOTATION_NOT_DRAWN` warning (status stays `ok`) with its id, kind and target. The longer
reference, with rows grouped by a field role, is
[Notes, risks and lanes](../../skills/chrona/references/notes-risks-and-lanes.md).

If your tasks are `scheduled` (an `amount` such as `15wd`, placed by its relations), change
the amount or the relation instead and read the new dates from `chrona schedule`; do not
compute them by hand. Check the edited plan:

```bash
chrona validate update-plan.yaml
chrona schedule update-plan.yaml
```

## 5. Render and read it

Pass the edited plan, the actuals and the baseline. The `target-b` preset draws the
baseline and the `Δ vs plan` column. The default preset accepts `--snapshot` but draws no
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
- **A row ending in `(removed)`:** a task the baseline had and the plan no longer has, drawn as a ghost
  (`(削除)` in `ja-JP`). In a View grouped by a field it closes the group the task had in the baseline, so a
  removed `mobile` task sits under `mobile` and not under the last group of the table; when no current task is in
  that group, the group follows the others. With a hierarchy or no grouping it is the last row.
- **Solid bar:** the current plan. **Dark line:** the actual. A striped bar is a task open
  at `asOf`.
- **A task that started on `asOf` has no actual bar yet.** An open task is drawn from its `start` up to
  `asOf`, so one that started today has no extent: nothing is drawn for it, its Δ cell stays blank and `render`
  warns `W_LAYOUT_OPEN_ACTUAL_INVALID`. It is not lost; the bar appears at the next update, when `asOf` is later.
- **`Δ vs plan`:** the Actual finish minus the **current** plan's finish, in **working days** of
  the object's calendar (the task's own `calendar`, else the project's `calendar`): the days
  from the planned finish up to, not including, the actual finish that the calendar marks
  working. A task still open is measured to `asOf`. If the plan declares no calendar every
  day counts, so the delta equals calendar days, as in this guide's plan. Design reads `+3d`
  (it finished 2026-11-12 against a planned 2026-11-09). With a Monday to Friday calendar, a
  task planned to finish on Friday 2026-11-06 and finished on Tuesday 2026-11-10 reads `+2d`
  (Friday and Monday), not `+4d`. This is the `target-b` preset's `deltaUnit: working-days`;
  a preset that sets `calendar-days` counts every day. Build's cell is **blank**
  because it has no finish yet: `target-b`, `yuya`, `titlecard`, `marquee` and `sunday` declare
  `missingBy: {inProgress: blank}` for this column. For a column you write, `missing` (or `missingBy`)
  sets what an open task shows, as in the column below. Moving the plan to match an actual makes its delta `+0d`, so
  the ghost, not the delta, shows how far the plan moved. This ordinary Actual comparison is
  against the current plan; it does not use the Snapshot as its delta baseline.

**A `Δ` column of your own.** The `Δ vs plan` column above is the design's: it declares its cell format. A column
you write in a View with `source: {facet: finishDelta}` and no `format` takes the design's `facet` column
style: the bundled presets except `editorial` (whose Layout mirrors the HALCYON-1 corpus) declare `format: signedDays`, so it reads `+5d*` for an estimated forecast. A design
of your own without that style draws the bare number (`5*`), without sign or unit; add `format: signedDays` to the
column or a `facet` style to its Layout Profile's `viewDefaults.columnStyles`. The unit text
follows `comparison.deltaUnit` and the locale (`d`, or `日` and `営業日` in `ja-JP`; see
[Locale and wording](locale-and-wording.md)):

```yaml
- {id: Delta, format: signedDays, header: {wording: column.finishDeltaBaseline}, source: {facet: finishDelta}, missing: blank, align: end, width: content, headerOrientation: horizontal}
```

To retain valid relation corridors across revisions, save the previous render
with `--emit-scene` and pass that JSON to the next render with
[`--previous-scene`](cli-reference.md#chrona-render). Both `first-fit` and `best`
revalidate it against the current marks, obstacles and routing policy before
reuse; an invalid route is searched again, never forced through a new obstacle.

`render` replaces an existing `--output` file without asking (`--output` says "an existing file
is replaced"). To keep the picture of an earlier update, choose a new name for each update, for
example `plan-2026-11-16.svg`. Warnings (`W_...`) are in the final JSON result on standard
output and do not change exit 0. Optional phase progress from `--progress` is written separately
to standard error.
[The diagnostics reference](../../skills/chrona/references/diagnostics.md) says what each
warning means.

## Focus a slide: hide finished work, show the next N weeks

For a short review, keep the full Project and filter only this View. The finished-state
predicate uses the current Actual set; a completed span needs an observed `finish` (a
completed point needs `at`). A relative window is anchored to `Actual.asOf`, so the Actual
file must declare it—Chrona does not substitute today's date, a Project date, or the
Snapshot date. This View shows one week before and six weeks after that date, and omits
rows whose selected time sources are entirely outside the interval:

<!-- chrona:doc-check file: focus-window.yaml -->
```yaml
version: chrona/view/v0.28
kind: view
id: website-focus-window
body:
  surface: table-timeline
  rows: {mode: automatic}
  selection:
    include: {}
    exclude: {state: [finished]}
  grouping: {by: none}
  ordering: {by: source, direction: ascending, tieBreak: id}
  tableColumns:
    - {id: Task, source: title, missing: em-dash, align: start, width: content, headerOrientation: horizontal}
  window: {mode: relative, before: 1w, after: 6w, outside: omit}
  comparison:
    baseline: snapshot
    actual: required
    observationSelection: latest
    deltaUnit: calendar-days
    facets: [planned, actual, finishDelta]
  visibility:
    labels: {placement: table, content: [title], side: end, overflow: suppress}
    relations: {mode: semantic, overflow: suppress}
    annotations: {mode: none, marker: none}
```

Render that focused slide with the same inputs:

```bash
chrona render update-plan.yaml --view focus-window.yaml --actual update-actual.yaml \
  --snapshot update-baseline.yaml --preset target-b --output update-focus.svg
```

Design is omitted because its observed finish is complete. Post-launch support falls
after the focused interval, so its row is omitted too. The `launch-to-support`
dependency still exists in the Project; because its endpoint is outside the window,
Layout reports `W_LAYOUT_RELATION_SUPPRESSED` rather than drawing a misleading connector
or silently deleting the relation. The warning and its source are in the final JSON on
standard output; optional progress remains on standard error.

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

2. Change the plan dates if what is left moved, then show slip against the original plan by
   rendering with `--forecast` under a new output name:

```bash
chrona render update-plan.yaml --actual update-actual-week2.yaml --snapshot update-baseline.yaml \
  --forecast --preset target-b --output update-after-week2.svg
```

The forecast compares its estimated finish with the supplied Snapshot baseline, not the edited
current plan. Its `Δ vs baseline` header names that reference. An unfinished forecast delta has
an asterisk (`*`); the `Forecast (* estimated)` legend key explains that it is an estimate. When
the forecast draws a different encoded colour, the key remains an explanation only and does not
claim that the estimate has a separate colour swatch.

What the draft path offers for writing actuals: edit or append to `actual.yaml` as above, or keep
the observations as columns (`progress`, `actual_start`, `actual_finish`) of the sheet you
[import](csv-import.md) with `chrona import --actual-output` (it never replaces a file, so write a
new one). There is no draft command that records an observation for you. `chrona actual-intake` does
that for a Store, from an intake batch command document (schema `actual-intake-batch`) and a
Store config; there is no step-by-step guide for it yet, so it is a known gap.

An AI coding agent finds the same loop in the [chrona agent skill](../../skills/chrona/SKILL.md#update-the-plan-after-a-week-of-work).
Reading a plan from a Store or a saved Render Context is a different path; see the
[progressive Project tutorial](progressive-project-tutorial.md).

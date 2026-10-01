# The authoring model, with one worked plan

Read this to know which file owns which decision. It restates no rule: the
specifications in `docs/specification/` of the chrona repository do (Spec 05 project
format, Spec 03 and 04 time and scheduling, Specs 06, 07 and 33 view, theme and layout).

## Who owns what

| Layer | Owns | You change it to |
| --- | --- | --- |
| Project | Objects, schedule modes, relations, calendars: the semantic truth | add, move or re-time work |
| View | Which objects and facts are shown, and in which rows | show a different subset |
| Theme | Concrete tokens: sizes, fonts, strokes | restyle without changing facts |
| Color Scheme | Which color each kind of thing gets | recolor |
| Layout | How the surface is composed | rearrange the page |
| CLI | Renders a deterministic picture from the five | nothing: never edit its output |

A preset (see `chrona preset list`) supplies View, Theme, Color Scheme and Layout together,
so the draft path needs only a Project (and an optional Actual Set for progress). A
renderer never writes anything back into the Project.

## A worked plan

`examples/launch.yaml` is a real plan: a kickoff gate, two tasks scheduled in working
days across a calendar exception (2026-11-23 is not a working day), and a launch gate with
a deadline. The tasks have no dates of their own; their dates come from the relations and
the calendar.

```yaml
version: timeline/v0.7
project:
  id: launch-plan
  title: Product launch
  calendar: office
calendars:
  office:
    working_days: [mon, tue, wed, thu, fri]
    exceptions:
      - {date: 2026-11-23, working: false}
objects:
  kickoff:
    type: gate
    title: Kickoff
    schedule: {mode: fixed-point, at: 2026-11-02}
  design:
    type: task
    title: Design
    calendar: office
    schedule: {mode: scheduled, amount: 5wd}
  build:
    type: task
    title: Build
    calendar: office
    schedule: {mode: scheduled, amount: 15wd}
  launch:
    type: gate
    title: Launch
    deadline: 2026-12-18
    schedule: {mode: fixed-point, at: 2026-12-14}
relations:
  - id: kickoff-to-design
    type: dependency
    from: {object: kickoff, endpoint: at}
    to: {object: design, endpoint: start}
    lag: 0d
  - id: design-to-build
    type: dependency
    from: {object: design, endpoint: end}
    to: {object: build, endpoint: start}
    lag: 0d
  - id: build-to-launch
    type: dependency
    from: {object: build, endpoint: end}
    to: {object: launch, endpoint: at}
    lag: 0d
```

Points to take from it:

- A gate is a point and has the endpoint `at`: `fixed-point` for a date it commits to, or
  `scheduled-point` for a date derived from its relations. A span (a task) has the
  endpoints `start` and `end`. A relation names an endpoint on each side; naming `start`
  on a gate is `E_ENDPOINT_MODE_MISMATCH`.
- `amount: 5wd` is a positive whole number of working days of the object's `calendar`. A
  `wd` amount with no calendar is `E_CALENDAR_REQUIRED`. These `amount` values are
  rejected as `E_SCHEMA`: `0wd`, `1.5wd`, `5 wd`, `5WD` and a bare number. Use `Nwd`.
- `launch` is `fixed-point` because 2026-12-14 is a promised date, with slack after the
  build. Never write a gate's date by reading it off `chrona schedule`: replace it with
  `schedule: {mode: scheduled-point}` and the gate lands on the build's end plus the
  relation's lag (here 2026-12-01). `constraints: {at: {min: 2026-12-07}}` is a
  not-earlier-than floor on it, `max` a hard cap that `chrona schedule` rejects with
  `E_CONTRADICTORY_BOUNDS` when the relations pass it. A `scheduled-point` needs a
  relation into its `at` or a `min` (`E_DERIVATION`).
- `lag: 0d` means the dependent starts the moment the predecessor ends.
- `deadline` is a promise, never a bound: it moves nothing. `chrona schedule` compares it
  with the planned finish (`at` of a point, `end` of a span) and lists a `W_DEADLINE`
  warning, with the days late, when the finish is later; the plan is still produced.
- Every object's `id` (`design`, `build`) is what an Actual Set refers to as
  `projectObjectId`.

`chrona schedule` returns these placements (its full output also has `diagnostics`,
`warnings` and an `analysis` of critical objects and float). `build` ends on 2026-12-01 because 15
working days from 2026-11-09 cross the exception on 2026-11-23:

```json
{
  "kickoff": {"at": "2026-11-02"},
  "design": {"start": "2026-11-02", "end": "2026-11-09"},
  "build": {"start": "2026-11-09", "end": "2026-12-01"},
  "launch": {"at": "2026-12-14"}
}
```

A test runs `chrona schedule` on the example and compares it with this block, and compares
the YAML above with `examples/launch.yaml`, so neither can drift.

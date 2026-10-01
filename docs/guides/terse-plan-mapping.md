# Terse plan: what a plan becomes in YAML

The [one-page card](terse-plan.md) teaches the syntax; this page shows what `chrona compile` writes for it. Each pair is checked by `tools/check_documented_commands.py`: the plan must compile, and the YAML below it must equal the compiler's output without its first line, a header comment that the compiler adds.

## A task, a task that follows it, and a gate

The first line gives the Project its id and title. A date span is `start..end` and its end is exclusive; `3d after a` is a three-day task that starts when `a` ends, so the compiler writes a `dependency` relation from the end of `a` to the start of `b` with a `0d` lag. The relation id is `FROM-TO`. A gate with a date is a fixed point (`at`), and its dependency lands on that point.

<!-- chrona:doc-check expect-yaml: next -->
```chrona
project first "First plan"
a "Design" task 2027-03-01..2027-03-08
b "Build" task 3d after a
c "Ready" gate 2027-03-20 after b
```

```yaml
version: timeline/v0.7
project:
  id: first
  title: First plan
objects:
  a:
    type: task
    title: Design
    schedule: {mode: fixed-span, start: '2027-03-01', end: '2027-03-08'}
  b:
    type: task
    title: Build
    schedule: {mode: scheduled, amount: 3d}
  c:
    type: gate
    title: Ready
    schedule: {mode: fixed-point, at: '2027-03-20'}
relations:
  - {id: a-b, type: dependency, from: {object: a, endpoint: end}, to: {object: b, endpoint: start}, lag: 0d}
  - {id: b-c, type: dependency, from: {object: b, endpoint: end}, to: {object: c, endpoint: at}, lag: 0d}
```

## A gate whose date is derived

A gate with no date and an `after` clause is a derived point: `mode: scheduled-point` stores no date, and `chrona schedule` places it on the earliest date its relations allow (here 2027-03-10 for `b`). `at >= D` is the floor, written `constraints.at.min` (`at <= D` is `constraints.at.max`, the cap). The dependent gate `c` follows `b.at`, and every relation into a gate targets `at`.

<!-- chrona:doc-check expect-yaml: next -->
```chrona
project derived "Derived gate"
a "Design" task 2027-03-01..2027-03-08
b "Review" gate after a +2d
c "Launch" gate at >= 2027-05-07 after b
```

```yaml
version: timeline/v0.7
project:
  id: derived
  title: Derived gate
objects:
  a:
    type: task
    title: Design
    schedule: {mode: fixed-span, start: '2027-03-01', end: '2027-03-08'}
  b:
    type: gate
    title: Review
    schedule: {mode: scheduled-point}
  c:
    type: gate
    title: Launch
    schedule: {mode: scheduled-point, constraints: {at: {min: '2027-05-07'}}}
relations:
  - {id: a-b, type: dependency, from: {object: a, endpoint: end}, to: {object: b, endpoint: at}, lag: 2d}
  - {id: b-c, type: dependency, from: {object: b, endpoint: at}, to: {object: c, endpoint: at}, lag: 0d}
```

## Lags, endpoints and a group

`+2d` is the lag and `.start` picks the start of `frame`. A group (`build`) carries its children by `parent` and takes its dates from them (`mode: rollup`); naming the group in `after` uses its end.

<!-- chrona:doc-check expect-yaml: next -->
```chrona
project groups "Groups"
build "Build" group
  frame "Frame" task 2027-03-01..2027-03-08
  fit "Fit-out" task 1w after frame +2d
check "Check" gate 2027-03-25 after build, frame.start
```

```yaml
version: timeline/v0.7
project:
  id: groups
  title: Groups
objects:
  build:
    type: group
    title: Build
    schedule: {mode: rollup}
  frame:
    type: task
    title: Frame
    parent: build
    schedule: {mode: fixed-span, start: '2027-03-01', end: '2027-03-08'}
  fit:
    type: task
    title: Fit-out
    parent: build
    schedule: {mode: scheduled, amount: 1w}
  check:
    type: gate
    title: Check
    schedule: {mode: fixed-point, at: '2027-03-25'}
relations:
  - {id: frame-fit, type: dependency, from: {object: frame, endpoint: end}, to: {object: fit, endpoint: start}, lag: 2d}
  - {id: build-check, type: dependency, from: {object: build, endpoint: end}, to: {object: check, endpoint: at}, lag: 0d}
  - {id: frame-check, type: dependency, from: {object: frame, endpoint: start}, to: {object: check, endpoint: at}, lag: 0d}
```

## A calendar and working days

`calendar standard mon-fri except DATE` declares the working week and its exceptions; with one calendar it is the project default, so `calendar: standard` appears on the project. `5wd` counts working days and `from DATE` anchors a duration. An object's own `calendar CAL` overrides the default for that object.

<!-- chrona:doc-check expect-yaml: next -->
```chrona
project cal "Calendar"
calendar standard mon-fri except 2027-03-05
design "Design" task 5wd from 2027-03-01
build "Build" task 3wd after design +1wd
```

```yaml
version: timeline/v0.7
project:
  id: cal
  title: Calendar
  calendar: standard
calendars:
  standard:
    working_days: [mon, tue, wed, thu, fri]
    exceptions:
      - {date: '2027-03-05', working: false}
objects:
  design:
    type: task
    title: Design
    schedule: {mode: scheduled, amount: 5wd, anchor: {start: '2027-03-01'}}
  build:
    type: task
    title: Build
    schedule: {mode: scheduled, amount: 3wd}
relations:
  - {id: design-build, type: dependency, from: {object: design, endpoint: end}, to: {object: build, endpoint: start}, lag: 1wd}
```

## A rejected plan

Every problem in a plan is reported at once, each with its source position and a hint, and nothing is written. The plan below is deliberately wrong (the doc-check expects `E_TERSE_KIND_UNKNOWN`); `chrona validate plan.chrona` prints this JSON and exits 1.

<!-- chrona:doc-check expect-error: E_TERSE_KIND_UNKNOWN -->
```chrona
project p "P"
build "Build" tsak 5d
```

```json
{
  "status": "rejected",
  "diagnostics": [
    {
      "code": "E_TERSE_KIND_UNKNOWN",
      "severity": "error",
      "component": "terse",
      "sourceRef": "/",
      "revisionRefs": [],
      "message": "unknown kind 'tsak'; known: task, gate, group (other types are written in YAML)",
      "source": "plan.chrona",
      "sourceRange": {
        "line": 2,
        "column": 15,
        "endLine": 2,
        "endColumn": 19
      },
      "hint": "did you mean `task`?"
    }
  ]
}
```

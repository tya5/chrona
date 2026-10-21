# Notes, risks and lanes by a field role

Use this when a plan needs a short remark on one task (a **note**), a flagged worry (a **risk**), and
rows grouped by who is responsible. All three belong to the plan file: the preset draws them, so you
never place a note on the picture. One file, shipped as `examples/notes-and-lanes/plan.yaml`: run the
commands from the skill directory.

## What to write

- **Notes and risks** are the top-level `annotations` map. Each entry has a `kind` (`note` or `risk`: the
  presets give each its own heading and colour), the `text`, and an `anchor: {object: ID}` naming the
  task or gate it is about. Keep the text to one short sentence; a long one does not fit the notes rail
  and the render warns `W_LAYOUT_LABEL_OVERFLOW`.
- **Lanes by a field role** need two things. The Project declares `fieldRoles: {responsible: team}`,
  which says that the object field `team` holds the owner (the closed roles are `responsible` and `phase`).
  Each object then carries the field under `fields`. A preset that groups (`target-b`, `executive-light`)
  draws one lane per owner; an object with no `team` goes to the preset's unassigned group.
  Lanes follow the order the plan lists their first object, and the unassigned group comes last. A task
  under a parent group does not repeat the lane's name: with a parent titled `Platform` in the `Platform`
  lane the row reads `Build`, not `Platform / Build`. A gate with no `team` stays in the unassigned group
  unless the View places points elsewhere (`rows.points`, for example `key-row`). The parent group's own
  summary row is not drawn; the render reports `I_VIEW_FIELD_GROUP_SUMMARIES_OMITTED` only when one
  parent's tasks fall in more than one lane.

```yaml examples/notes-and-lanes/plan.yaml
version: timeline/v0.7
project:
  id: notes-demo
  title: Notes, risks and lanes
  calendar: office
fieldRoles:
  responsible: team
calendars:
  office:
    working_days: [mon, tue, wed, thu, fri]
objects:
  kickoff:
    type: gate
    title: Kickoff
    schedule: {mode: fixed-point, at: '2026-11-02'}
  design:
    type: task
    title: Design
    fields: {team: Platform}
    schedule: {mode: fixed-span, start: 2026-11-02, end: 2026-11-09}
  build:
    type: task
    title: Build
    fields: {team: Platform}
    schedule: {mode: scheduled, amount: 10wd}
  test:
    type: task
    title: Test
    fields: {team: Product}
    schedule: {mode: scheduled, amount: 5wd}
  launch:
    type: gate
    title: Launch
    schedule: {mode: scheduled-point}
relations:
- {id: design-to-build, type: dependency, from: {object: design, endpoint: end}, to: {object: build, endpoint: start}, lag: 0d}
- {id: build-to-test, type: dependency, from: {object: build, endpoint: end}, to: {object: test, endpoint: start}, lag: 0d}
- {id: test-to-launch, type: dependency, from: {object: test, endpoint: end}, to: {object: launch, endpoint: at}, lag: 0d}
annotations:
  vendor:
    kind: note
    text: Slot confirmed for 9 Nov.
    anchor: {object: build}
  signing:
    kind: risk
    text: Keys not yet issued.
    anchor: {object: test}
```

```bash
chrona validate examples/notes-and-lanes/plan.yaml
chrona schedule examples/notes-and-lanes/plan.yaml
chrona render examples/notes-and-lanes/plan.yaml --preset target-b --output notes-and-lanes.svg
```

The picture has two lanes (`Platform`, `Product`), a third for the two gates that have no `team`, and two
boxes on the notes rail headed `NOTE · build` and `RISK · test`, each joined to its task by a leader line.
Edit `annotations` or `fields` in the plan and render again.

## What the warnings mean

`render` prints `I_VIEW_FIELD_ROLE_UNBOUND` for the role `phase`, which this plan does not declare: the
preset's phase column falls back, harmlessly. If a plan declares no `responsible` role, the preset groups
by its fallback instead of by owner; declare the role to get the lanes. A crowded rail can report
`W_LAYOUT_ROUTE_FALLBACK` naming the leader of one note: the leader is drawn as a straight line; shorten
the notes or widen `--viewport`. [diagnostics.md](diagnostics.md) explains the other codes.

The rules are in Spec 05, sections 10.1 (field roles) and 12 (annotations).

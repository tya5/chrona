# Terse plan syntax: the one-page card

A terse plan is a short text file (`plan.chrona`) that `chrona compile` turns into a Chrona Project (`project.yaml`).
Use it to draft a schedule fast: one line per task, gate or group, dependencies as a clause on the line. The
compiler checks the plan, reports every error with a line and column, and hands the Project to the normal
validator. Normative rules: [Spec 65](../specification/65-terse-plan-syntax.md).

## The loop

<!-- chrona:doc-check skip: needs the plan file written by the author -->
```sh
chrona compile plan.chrona -o project.yaml
chrona validate project.yaml
chrona schedule project.yaml
```

1. Write `plan.chrona`. 2. Compile. Success prints nothing and writes `project.yaml` (it never overwrites an existing
file: delete it first). 3. On failure you get JSON with `code`, `message`, `hint` and `sourceRange` (line, column)
for every problem at once: fix them all, compile again. With no `-o` the YAML goes to stdout and the error JSON to
stderr, so `chrona compile plan.chrona > project.yaml` never puts an error into the file.
<!-- chrona:doc-check skip: needs the plan file written by the author -->
```sh
chrona compile plan.chrona --output project.yaml
```
4. `chrona validate` and `chrona schedule` check the dates (a cycle or a gate earlier than what it follows shows up
there). After that, `project.yaml` is the only source of truth; the plan is retired.

## Shape of a plan

```chrona
terse 0.1
project my-plan "My plan" calendar standard
calendar standard mon-fri except 2027-04-02 2027-05-31

# NAME "Title" KIND  schedule  [calendar CAL]  [after DEP, DEP ...]
kickoff "Kickoff" gate 2027-03-01
design "Design" task 10wd from 2027-03-02
build "Build" task 20wd after design +1wd
review "Design review" gate 2027-05-07 after design.start
phase-2 "Phase 2" group
  tests "Tests" task 5wd after build
  launch "Launch" gate 2027-06-30 after tests +2d, review
```

One statement per line, `#` starts a comment. Order: optional `terse 0.1`, then one `project`, then `calendar`
lines, then objects (objects may refer to objects defined later).

## Statements

- `project ID "Title" [calendar CAL]`: id is one word, title is optional.
- `calendar CAL DAYS [except DATE ...] [work DATE ...]`: `DAYS` is `mon-fri`, `mon-wed,fri`, `sat,sun`. `except` lists
  non-working dates, `work` extra working dates. With exactly one calendar it is the project default; with two or
  more, say which on the project line (`project p "P" calendar standard`) or on each object.
- `NAME ["Title"] KIND SCHEDULE [calendar CAL] [after DEP, ...]` for an object; the parts come in that order
  (`calendar CAL` before `after`).

**NAME** (and calendar names): lower-case letters, digits, hyphens, starting with a letter (`bus-test`). It is the
id forever; you must invent one for every object. Not allowed as a name: `terse project calendar task gate group
after from until in except work start end at`. Names such as `on`, `no` or `null` are fine.
**Title**: always in double quotes (`"Design review"`); `\"` and `\\` are the only escapes. Titles may be any text.
**KIND**: `task`, `gate` or `group`, nothing else.

## Schedules (after the kind)

| Write | Meaning |
| --- | --- |
| `2027-03-05` | a fixed date (a gate, usually) |
| `2027-03-01..2027-03-08` | a fixed span; the end date is **exclusive**; no spaces around `..` |
| `5d`, `2w`, `20wd` | a duration: calendar days, weeks, working days (`wd` needs a calendar) |
| `20wd from 2027-03-22` | a duration starting on that date (`until DATE` ends on it) |
| `5wd start >= 2027-03-01 end <= 2027-04-30` | optional bounds after a duration (`start`/`end`, `>=`/`<=`) |
| `group` (nothing after it) | a group: its dates come from its children |

Dates are `YYYY-MM-DD`, zero padded, real dates. Durations are whole numbers with a unit: `20` and `2mo` are errors.
**A duration needs a start**: give it `from DATE` or an `after` dependency, or `chrona schedule` cannot place it.

## Dependencies: `after`

`after a, b +2d, c.start` means "this object comes after a, after b with 2 days of lag, after the start of c".
A lag is a signed amount with the sign attached: `+1wd`, `-2d` (never `+ 1wd`); add `in CAL` to count it in another
calendar (`+1wd in range`). A lag in `wd` needs a calendar. Plain `after x` uses the end of a duration or group and
the date of a fixed date; add `.start`, `.end` or `.at` to pick (a fixed date has only `.at`).
Groups: indent children by exactly two spaces under the group line; groups nest. A group takes no schedule, no
`calendar` and no `after`, but it can be named in someone else's `after`.

## What the syntax cannot say

Owners, teams, phases (`fields`), planned progress, deadlines, links, WBS codes, annotations, scenarios, other
object types than `task`/`gate`/`group`. When you need them: compile first, then edit `project.yaml` by hand.

## Frequent errors

| You wrote | Error and fix |
| --- | --- |
| `design Build the thing task 5d` | `E_TERSE_TITLE_UNQUOTED`: quote the title |
| `design tsak 5d` | `E_TERSE_KIND_UNKNOWN`: use `task`, `gate` or `group` |
| `task design 5d` | `E_TERSE_NAME_RESERVED`: the name comes first |
| `Build_Phase task 5d` | `E_TERSE_NAME_INVALID`: use `build-phase` |
| `pdr gate` | `E_TERSE_SCHEDULE_REQUIRED`: a gate needs a date |
| `a task 20` or `3 days` | `E_TERSE_AMOUNT_INVALID`: write `20d` |
| `pdr gate 2027-3-5` | `E_TERSE_DATE_INVALID`: write `2027-03-05` |
| `after structur` | `E_TERSE_REFERENCE_UNKNOWN`: the hint names the closest object |
| `a task 5wd` and no calendar | `E_CALENDAR_REQUIRED`: add `calendar standard mon-fri` |

Anything else Core finds (an empty group, an empty span) keeps its Core code and gets a position too.

```chrona
terse 0.1
project three-lines "Three lines"
a "Draft" task 2027-03-01..2027-03-08
b "Review" task 3d after a
c "Ship" gate 2027-03-20 after b
```

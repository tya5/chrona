# Terse plan syntax: the one-page card

A terse plan (`plan.chrona`) has one line per task, gate or group; `validate`, `schedule`, `render` and `compile`
accept it directly. Compilation reports positioned errors and emits a Chrona Project (`project.yaml`). See [Spec 65](../specification/65-terse-plan-syntax.md),
[the YAML mapping](terse-plan-mapping.md) or [CSV import](csv-import.md) for the full rules and alternatives.

## The loop

<!-- chrona:doc-check skip: needs the plan file written by the author -->
```sh
chrona validate plan.chrona
chrona schedule plan.chrona
chrona render plan.chrona --output plan.svg
chrona compile plan.chrona --output project.yaml
```

1. Write `plan.chrona`. 2. `validate` checks the structure and dependency cycles; `schedule` places the dates (a gate earlier
than what it follows is reported there; a finding of either carries the plan's line); `render` draws it, byte-identical to compiling and
then rendering the YAML (`--preset`, `--actual` and the other flags work as for YAML). 3. A plan that does not
compile prints JSON with `code`, `message`, `hint` and `sourceRange` (line, column) for every problem at once: fix
them all, run again. 4. When the plan is final, `compile` writes `project.yaml` (it never overwrites an existing
file: delete it first); from then on the YAML is the only source and the plan is retired. Only these four commands
read a plan; every other command reads YAML. Without `-o`, `compile` sends the YAML to stdout and the error JSON to
stderr, so `chrona compile plan.chrona > project.yaml` never puts an error into the file.

## Shape of a plan

```chrona
terse 0.1
project my-plan "My plan" calendar standard
calendar standard mon-fri except 2027-04-02 2027-05-31

# NAME "Title" KIND  schedule  [calendar CAL]  [after DEP, DEP ...]  [deadline D]
kickoff "Kickoff" gate 2027-03-01
design "Design" task 10wd from 2027-03-02
build "Build" task 20wd after design +1wd deadline 2027-05-14
review "Design review" gate 2027-05-07 after design.start
phase-2 "Phase 2" group
  tests "Tests" task 5wd after build
  launch "Launch" gate 2027-06-30 after tests +2d, review
```

One statement per line, `#` starts a comment. Order: optional `terse 0.1`, then one `project`, then `calendar`
lines, optional `entity` lines, then objects (objects may refer to objects defined later).

## Statements

- `project ID "Title" [calendar CAL]`: id is one word, title is optional; it may end with `extension PACKAGE "PATH" REVISION`
  (repeat for unique IDs; paths are relative to the Project directory: source for direct/stdout, output parent for `compile -o`).
- `calendar CAL DAYS [except DATE ...] [work DATE ...]`: `DAYS` is `mon-fri`, `mon-wed,fri`, `sat,sun`. `except` lists
  non-working dates, `work` extra working dates. With exactly one calendar it is the project default; with two or
  more, say which on the project line (`project p "P" calendar standard`) or on each object.
- `entity ID "Title" PROFILE`: a minimal entity (type and title) for `KEY=ID` references such as `deliverable=del-portal`;
  after the calendars, before objects; PROFILE must come from a declared package (`E_TERSE_PROFILE_UNKNOWN`).
- `NAME ["Title"] KIND [profile ID] SCHEDULE [calendar CAL] [after DEP, ...] [deadline DATE] [KEY=VALUE ...]`: profile follows KIND;
  assignments finish the line. `calendar CAL` overrides the project default for `wd` amounts; a deadline moves nothing.
  Scalar values include `risk=high`, `flag=true` or `note="two words"`; assignments need a profile; quotes keep strings.

**NAME** (and calendar names): lower-case letters, digits, hyphens, starting with a letter (`bus-test`). It is the
id forever; invent one for every object. Not allowed as a name: `terse project calendar task gate group
after from until in except work start end at`. Names such as `on`, `no` or `null` are fine.
**Title**: always in double quotes (`"Design review"`); `\"` and `\\` are the only escapes. **KIND**: `task`, `gate`, `group`.

## Schedules (after the kind)

| Write | Meaning |
| --- | --- |
| `2027-03-05` | a fixed date (a gate, usually) |
| nothing, on a gate with `after` | a derived date: the earliest its dependencies allow (below) |
| `2027-03-01..2027-03-08` | a fixed span; the end date is **exclusive**; no spaces around `..` |
| `5d`, `2w`, `20wd` | a duration: calendar days, weeks, working days (`wd` needs a calendar) |
| `20wd from 2027-03-22` | a duration starting on that date (`until DATE` ends on it) |
| `5wd start >= 2027-03-01 end <= 2027-04-30` | optional bounds after a duration (`start`/`end`, `>=`/`<=`) |
| `group` (nothing after it) | a group: its dates come from its children |

Dates are `YYYY-MM-DD`, zero padded, real dates. Durations are whole numbers with a unit: `20` and `2mo` are errors.
**A duration needs a start**: give it `from DATE` or an `after` dependency, or `chrona schedule` cannot place it.

## Dependencies: `after`

`after a, b +2d, c.start +1w` means "this object comes after a, after b with 2 days of lag, after the start of c
with a week of lag". A lag is a signed amount with the sign attached and the unit `d`, `w` or `wd`: `+1wd`, `-2d`,
`+1w` (never `+ 1wd`). A `wd` lag without `in CAL` is counted on the calendar of the object that carries the `after`
(its own `calendar CAL`, else the project default), not the predecessor's; add `in CAL` to count it elsewhere
(`+1wd in range`). A `wd` lag needs a calendar. Plain `after x` uses the end of a duration or group and the date of
a fixed date; add `.start`, `.end` or `.at` to pick (a fixed date has only `.at`).
Groups: indent children by exactly two spaces under the group line; groups nest. A group takes no schedule, no
`calendar` and no `after`, but it can be named in someone else's `after`.

## Gates: a date, or derived from `after`

A gate with no date and an `after` clause takes the earliest date its dependencies allow, so never compute it by hand.
`at >= D` is a not-earlier-than floor and `at <= D` a hard cap, written before `after`; a floor alone is just a date
(`gate D`). A gate with a date is fixed: `chrona schedule` rejects it (`E_FIXED_TARGET_VIOLATION`, naming the date to
write) when its dependencies end later; `E_CONTRADICTORY_BOUNDS` rejects a derived gate pushed past its cap.

```chrona
project p "P"
design "Design" task 2027-03-01..2027-03-08
review "Review" gate after design +2d                   # derived: 2027-03-10
launch "Launch" gate at >= 2027-05-07 after review +2d  # the floor wins: 2027-05-07
```

## What the syntax cannot say

Arrays/maps, arbitrary Project extension forms, entity fields, progress, links, WBS codes, annotations,
scenarios, and presentation remain YAML-only. Compile first, then edit `project.yaml` by hand.

## Frequent errors

| You wrote | Error and fix |
| --- | --- |
| `design Build the thing task 5d` | `E_TERSE_TITLE_UNQUOTED`: quote the title |
| `design tsak 5d` | `E_TERSE_KIND_UNKNOWN`: use `task`, `gate` or `group` |
| `task design 5d` | `E_TERSE_NAME_RESERVED`: the name comes first |
| `pdr gate` | `E_TERSE_SCHEDULE_REQUIRED`: a gate needs a date, or `after X` to derive it |
| `after structur` | `E_TERSE_REFERENCE_UNKNOWN`: the hint names the closest object |
| `a task 5wd` and no calendar | `E_CALENDAR_REQUIRED`: add `calendar standard mon-fri` |

Anything else Core finds (an empty group, an empty span) keeps its Core code and gets a position too.

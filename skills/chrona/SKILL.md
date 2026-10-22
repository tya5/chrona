---
name: chrona
description: Plan a project timeline, Gantt chart, roadmap slide, milestone schedule, or plan-versus-actual review from a YAML file, with the dates computed from durations, working-day calendars and dependencies instead of drawn by hand. Use it when the user asks for a Gantt chart, a project timeline, a schedule with dependencies, lags, deadlines or working days, a milestone or roadmap slide, or a plan versus actual comparison, and the picture will be edited and re-rendered, or the plan will be updated as work progresses and compared with an earlier plan and with actuals. The chrona CLI computes the dates, draws every revision in the same design, and compares plan with actual; the agent edits the plan, never the picture. To update an existing plan (record actuals, move asOf, re-plan, compare with the saved plan), read the section "Update the plan after a week of work".
---

# chrona

Chrona computes a schedule and picture from YAML. Edit the plan, never the generated picture.

## When to use it

- Dates must be right: durations in working days, a holiday calendar, dependencies, lags.
- The plan will be edited and re-rendered, a reviewer will diff the result, and each revision will be compared with the earlier plan and actual progress.

For a README/PR sketch or decorative one-off, read
[references/mermaid-or-chrona.md](references/mermaid-or-chrona.md) first: Chrona is the wrong tool.

## Rules that cost the most when broken

1. **Never hand-write or edit SVG.** Chrona derives it. A hand-placed bar is correct only
   until someone edits the plan, because nothing recomputes it.
2. **Never compute a date by hand.** Read it from `chrona schedule`. An `end` is
   exclusive: it is the first day after the last day of work. A 5-working-day task that
   starts on Monday 2026-11-02 ends on Monday 2026-11-09, and a 15-working-day task whose
   range crosses a calendar exception ends later than a plain count says (in the worked
   example, 2026-12-01 instead of 2026-11-30). A gate that follows its work is no exception:
   do not read its date off the plan and write it. Declare it `scheduled-point`, with no
   date, and `chrona schedule` derives it. Write a `fixed-point` date only for a date that
   is promised, not one that is computed.
3. **Edit `project.yaml`, then render again.** Never edit the generated picture.
4. **Run `chrona schedule`, not only `chrona validate`.** `validate` finds structure
   errors and dependency cycles, but it computes no dates: a fixed date that contradicts
   its dependencies and contradictory bounds pass `validate` (`{"status": "ok", "diagnostics": []}`) and are rejected
   by `schedule` and `render`.
5. **Copy a preset once, then edit the copy.** Do not edit a copied preset in place to
   change one token each time; do not edit the files inside the installed package.
6. **A rejected command is information.** Read `code` and `sourceRef` first.
   [references/diagnostics.md](references/diagnostics.md) says what each code means and
   what to change.

## The loop

Start from a working plan, change it, check it, draw it:

```bash
chrona init my-plan
chrona validate my-plan/project.yaml
chrona schedule my-plan/project.yaml
chrona render my-plan/project.yaml --output my-plan/plan.svg
```

`chrona init DIR` writes `project.yaml` (two tasks and a gate) and `actual.yaml`
(observed progress for the same ids) and refuses to write into a directory that already
exists. Edit `project.yaml`, then repeat `validate`, `schedule` and `render`. Pass
`--actual my-plan/actual.yaml` to `render` to draw progress over the plan. `--output` is
required, and its suffix picks the format: `.svg`, `.png` and `.pdf` (need `pip install
'chrona[render]'`), or `.typ` (Typst source: it names the installed font family, so compile it
where that font exists). `chrona validate my-plan/actual.yaml` checks an Actual Set too.

The result of every command is JSON on standard output. A command that
rejects the plan prints `{"status": "rejected", "diagnostics": [...]}` and exits 1; a bad
file, flag or output suffix exits 2; success exits 0.

## Update the plan after a week of work

Plain files, no Store. Run from the skill directory; the worked files are `examples/launch.yaml`
(plan) and `examples/actual.yaml` (a complete Actual Set for it: copy and edit it).

1. **Keep the baseline:** `cp project.yaml baseline.yaml`; never edit the copy. `baseline-capture` needs a Store.
2. **Record actuals** in `actual.yaml`. Each observation is `{id, sequence, projectObjectId, actual}` and
   `actual` is: `start` and `finish` (the day **after** the last day worked) for a finished task; `start`,
   `openUntil: asOf` and `progress` below 1, no `finish`, for an open one; `at` for a gate. Next week append
   observations with a higher `sequence` (the highest wins). No command writes one; a sheet with
   `progress`/`actual_*` columns can go through `chrona import` (below).
3. **Move `asOf`** (`body.asOf`) to the day the observations are true on. Before any actual exists use the
   plan's first day (or today); it draws the TODAY marker and never changes a plan date.
4. **Re-plan** in `project.yaml`: edit `at` of a `fixed-point` gate, `start`/`end` (`end` exclusive) of a
   `fixed-span`, or the `amount`/`lag` of a `scheduled` item. Read dates from `chrona schedule`, not by hand.
5. **Render against the baseline** with a preset that draws one (`chrona preset list` names them):

```bash
chrona render examples/launch.yaml --actual examples/actual.yaml --snapshot examples/launch.yaml --preset target-b --output update.svg
```

Here plan and baseline are one file; in an update, your edited plan and the step 1 copy. Use a new
output name each time. A dashed outline is where the baseline had an item that moved.
For a forecast instead of editing dates, use `chrona render project.yaml --actual actual.yaml --snapshot baseline.yaml --forecast --preset target-b --output forecast.svg`. It uses `body.asOf` without changing Project, Actual or baseline files or saving a Snapshot. Unfinished Δ carries `*` against the baseline (the original plan when omitted); progress is not remaining effort. `technical-print` and MCP `render_draft` support forecast too. Omit the flag for the unchanged ordinary plan/actual render.

## If the chrona MCP server is connected

When the host lists chrona tools (an MCP server the user started), prefer them: they run
the same code as the commands above, take paths relative to the workspace root, and return
the same diagnostics as JSON. Otherwise use the commands. Read a result's `status` (`ok`,
`rejected` or `failed`), not only the tool's error flag: a rejected plan is a normal result.

| Tool | Same as | Note |
| --- | --- | --- |
| `validate_project` | `chrona validate` | Structure and dependency cycles, no dates: run `schedule_project` for those. |
| `schedule_project` | `chrona schedule` | Placements, critical path and `W_DEADLINE` warnings; also rejects a date or bound the dependencies contradict. |
| `render_draft` | `chrona render` | A PNG preview, or the SVG with `inline: svg`; writes no file. |
| `list_presets` | `chrona preset list` | The ids `render_draft` takes as `preset`. |
| `render_review` | `chrona render-review` | Pinned evidence: renders an immutable Render Context from a Store (see below); read-only. |
| `compare_baseline` | `chrona baseline-compare` | What changed between a named baseline and a candidate Project in a Store; read-only. |
| `check_command` | `chrona command-check` | Previews an inline Store command or contained command file; writes nothing. |
| `apply_command` | `chrona command-apply` | Applies that command to the Store. It runs only if the user started the server with `--allow-write`. |
| `apply_authoring_command` | `chrona authoring-command-apply` | Applies an inline authoring command or contained command file; requires `--allow-write`. |
| `create_workspace` | Library entry (no CLI equivalent) | Creates a new workspace directory from a builtin preset and compact project; requires `--allow-write`. |
| `validate_workspace` | Library entry (no CLI equivalent) | Validates a workspace and its complete preset/resource closure; returns its revision. |
| `workspace_revision` | `chrona workspace revision` | Reads the current guided workspace revision. |
| `render_workspace` | `chrona render-workspace` | Renders a guided workspace using its copied preset; writes no output file. |
| `create_project` | Library entry (no CLI equivalent) | Creates a new `project.yaml` from a complete Project; requires `--allow-write`. |
| `apply_project_command` | Library entry (no CLI equivalent) | Edits `project.yaml` (objects, relations, calendars, entities, field roles, annotations, project meta) at a `baseRevision`; the accepted result's `inverse` reverts it; requires `--allow-write`. |

Edit standalone `project.yaml` directly, or over MCP with `apply_project_command` (`validate_project` returns its `projectRevision`); use `apply_command` for Stores. For guided MCP-only editing and revision handling, read [guided workspaces](references/guided-workspaces.md).

## The model in five lines

- **Project** is the semantic truth: objects, schedule modes, relations, calendars.
- **View** selects what is shown and in which rows.
- **Theme** paints (tokens such as sizes and fonts); a **Color Scheme** assigns colors.
- **Layout** composes the surface.
- **The CLI renders**, and nothing a renderer produces is ever read back as project data.

The plan is a YAML file. Each object has a `schedule` in one of five modes: `fixed-point`
(`at`, a gate on a date it commits to), `scheduled-point` (a gate with no date: the earliest
its relations allow), `fixed-span` (`start` and `end`), `scheduled` (an
`amount` such as `15wd`, placed from its relations and its calendar) and `rollup`. A
relation joins two endpoints and has a `lag`. The worked example, with all of it, is in
[references/authoring-model.md](references/authoring-model.md) and lives as a file at
`examples/launch.yaml`. For typed fields and a colour by one, read [references/typed-fields.md](references/typed-fields.md); for notes, risks and rows grouped by a field role, read [references/notes-risks-and-lanes.md](references/notes-risks-and-lanes.md).

## Check the worked example
Run from the skill directory (it holds this file).

```bash
chrona validate examples/launch.yaml
chrona schedule examples/launch.yaml
chrona render examples/launch.yaml --output launch.svg
```

## Change the look, not the plan

One command draws with the packaged default look. A **preset** bundles View, Theme,
Color Scheme and Layout, so a different preset changes the look without touching the
plan. List the builtin ids, render with one, or copy one to edit (`--id NAME` on a copy renames the preset and all its resource ids together):

```bash
chrona preset list
chrona render examples/launch.yaml --preset editorial --output launch-editorial.svg
chrona preset copy executive-light --output looks/executive-light
chrona render examples/launch.yaml --preset looks/executive-light/preset.yaml --output launch-executive.svg
```

[Theme role reference](references/theme-role-reference.md) explains what roles paint and which
properties consume tokens.
`--viewport WIDTHxHEIGHT` sets a finite minimum size (the default is `1600xauto`); a narrower one can clip or drop labels. Use explicit `--view`, `--theme`, `--scheme` or `--layout` files only to override one member of a preset. Contexts and Stores are the pinned-evidence path below; do not use them unless the user asks for pinned evidence.

## Pinned evidence from a Store (only when the user asks)

`render` draws a draft of a Project file. An immutable **Render Context** (Project, View, Theme,
Color Scheme, Layout and fonts, each pinned by a content identity) lives in a **Store**
named by a **Store configuration** (`.chrona/store.yaml`); a reference file points at one resource in it. `render_review` renders a
Context's reference exactly; `compare_baseline` compares a named baseline with a candidate Project.
Both only read and refuse a Store root outside the workspace or bytes that do not match their
pinned identity. Do not edit a Store file, unpin a reference or change `integrity` to make a call pass: that
is the user's. Without the tools, `chrona render-review` and `chrona baseline-compare` do the same.

## Start from a spreadsheet

Export CSV (or TSV), then `chrona import plan.csv --output project.yaml` (add `--actual-output actual.yaml
--as-of DATE` for `progress`/`actual_*` columns, `--calendar "standard mon-fri"` for `wd` durations). One row
per task, gate or group; only `id` is required. Columns: `title`, `type` (task, gate, group), `start`, `end`
(exclusive), `finish` (inclusive), `duration`, `parent`, `predecessors`, `deadline`, `calendar`, `progress`,
`actual_start`, `actual_finish`; any other column is a text field. `chrona import --help` has the details.
`--role responsible=team` binds an extra column as the owner: a lane-grouping preset (`executive-light`,
`target-b`) then draws one lane per owner and a group is a plain row, not a lane. It never overwrites a file.

## Warnings and diagnostics

Errors are JSON on standard output with exit 1 or 2. A render that succeeds exits 0 and prints
`{"status": "ok", "diagnostics": [], "warnings": [...]}` on standard output. Phase progress
uses terminal stderr or `--progress`; expensive-routing advice is printed early even on a quiet pipe:
read `warnings` for `W_...` and `I_...` entries, such as something clipped, suppressed or substituted. Read the code in
[references/diagnostics.md](references/diagnostics.md); shorten a title, widen `--viewport`, or
accept it. `.typ` or `.tex` of a preset with viewer-fit (`target-b`, `sunday`) warns `W_VIEWER_FIT_NOT_HONOURED`: harmless, that text is drawn plain. If that file does not list a code, rerun the smallest plan that shows it, quote the
whole diagnostic to the user, and do not guess a fix.

## What chrona does not do

No resource leveling, no interactive editing, no cycle analysis (a cycle is rejected). A `deadline` is a promise, not a bound: `chrona schedule` still places everything and
lists a `W_DEADLINE` for each object planned after it (`render` lists it in `warnings`);
`validate` does not judge it. A View can draw it (`deadlines: {show: slipped}`), and a terse plan
states it with a last clause, `deadline 2027-06-30`.

## Install, refresh, and where the rules live

This skill ships with chrona. `chrona skill copy DIR` writes into an empty or absent directory,
such as `.claude/skills/chrona`; `E_SKILL_OUTPUT_EXISTS` refuses a nonempty destination.
After upgrading, copy into a new directory, compare with `diff -r`, and replace the old one.
Rules: Spec 05 (Project), Spec 04 (scheduling), and Specs 06, 07 and 33 (View, Theme, Layout).

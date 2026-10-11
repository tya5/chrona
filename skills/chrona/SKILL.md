---
name: chrona
description: Plan a project timeline, Gantt chart, roadmap slide, milestone schedule, or plan-versus-actual review from a YAML file, with the dates computed from durations, working-day calendars and dependencies instead of drawn by hand. Use it when the user asks for a Gantt chart, a project timeline, a schedule with dependencies, lags, deadlines or working days, a milestone or roadmap slide, or a plan versus actual comparison, and the picture will be edited and re-rendered or must be reproducible. The chrona CLI computes the schedule and draws a deterministic SVG (or PNG) from the plan; the agent edits the plan, never the picture.
---

# chrona

Chrona turns a YAML plan into a computed schedule and a deterministic picture. You
write and edit the plan; the `chrona` command computes every date and draws every
pixel. An identical input produces identical bytes, so a changed SVG means a changed plan.

## When to use it

- Dates must be right: durations in working days, a holiday calendar, dependencies, lags.
- The plan will be edited and re-rendered, or a reviewer will diff the result.
- The picture must be reproducible next quarter, or compared with actual progress.

For a quick sketch inside a README or pull request, or for a decorative one-off picture,
read [references/mermaid-or-chrona.md](references/mermaid-or-chrona.md) first. Chrona is
the wrong tool there, and the file says so honestly.

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
required, and its suffix picks the format: use `.svg`, or `.png` (needs `pip install
'chrona[render]'`). Other suffixes need options this skill does not cover.

The result of `validate` and `schedule` is JSON on standard output. A command that
rejects the plan prints `{"status": "rejected", "diagnostics": [...]}` and exits 1; a bad
file, flag or output suffix exits 2; success exits 0.

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
| `check_command` | `chrona command-check` | Previews a Store command (an Actual intake batch or a baseline capture); writes nothing. |
| `apply_command` | `chrona command-apply` | Applies that command to the Store. It runs only if the user started the server with `--allow-write`. |

No tool writes the plan. Edit `project.yaml` with your own file tools, then call the
tools again. `apply_command` changes a Store, never the plan, and has no approval step of
its own: apply only what the user asked for. A stale `baseRevision` is rejected, a repeated
`commandId` is a no-op, and nothing is overwritten.

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
`examples/launch.yaml`.

## Check the worked example

These commands use the repository-relative path; in an installed copy of this skill,
prefix `skills/chrona/` with the directory that holds the skill (for example
`.claude/skills/chrona/`).

```bash
chrona validate skills/chrona/examples/launch.yaml
chrona schedule skills/chrona/examples/launch.yaml
chrona render skills/chrona/examples/launch.yaml --output launch.svg
```

## Change the look, not the plan

One command draws with the packaged default look. A **preset** bundles View, Theme,
Color Scheme and Layout, so a different preset changes the look without touching the
plan. List the builtin ids, render with one, or copy one to edit:

```bash
chrona preset list
chrona render skills/chrona/examples/launch.yaml --preset editorial --output launch-editorial.svg
chrona preset copy executive-light --output looks/executive-light
chrona render skills/chrona/examples/launch.yaml --preset looks/executive-light/preset.yaml --output launch-executive.svg
```

`--viewport WIDTHxHEIGHT` sets a finite minimum size (the default is `1600xauto`). A
narrower viewport can clip or drop labels; see the warnings below.

Reach for explicit `--view`, `--theme`, `--scheme` or `--layout` files only to override
one member of a preset. Immutable Render Contexts, snapshots and Store configuration are
the pinned-evidence path (next section); do not use them unless the user asks for pinned evidence.

## Pinned evidence from a Store (only when the user asks)

`render` draws a draft of a Project file. Evidence that must be reproducible is another path: an
immutable **Render Context** (the closed list of Project, View, Theme, Color Scheme, Layout and fonts
to render, each pinned by a content identity) lives in a **Store**, which a **Store configuration**
(`.chrona/store.yaml`) names. A reference file (`id`, `kind`, `store`, `address`, `revision`,
`contentIdentity`) points at one resource in it. `render_review` takes the Context's reference file and
renders exactly that, in the Context's own format and viewport (so it has no `preset` or `viewport`);
`compare_baseline` takes the reference of a named baseline (an immutable snapshot of a Project) and a
candidate Project's reference and returns what changed. Both only read, refuse a Store root outside the workspace, and refuse bytes that do not
match the pinned identity; no argument loosens that. Do not edit a Store file or unpin a reference to
make a call pass, and do not change a Store's `integrity` setting: it is the user's. Without the tools,
`chrona render-review` and `chrona baseline-compare` do the same work.

## Warnings and diagnostics

Errors are JSON on standard output with exit 1 or 2. A render that succeeds can still
print warnings (`W_...`) and notes (`I_...`) as JSON lines on standard error with exit 0:
something was clipped, suppressed or substituted. A warning carries a code and its facts
but no explanation, so read it in [references/diagnostics.md](references/diagnostics.md).
Shorten a title, widen `--viewport`, or accept it.

If a command reports a code that file does not list, run it again with the smallest plan
that shows it, quote the whole diagnostic to the user, and do not guess a fix.

## What chrona does not do

No resource leveling at this surface, no interactive editing, no cycle analysis (a
cycle is rejected). A `deadline` is a promise, not a bound: `chrona schedule` still places
everything and lists a `W_DEADLINE` in its `warnings` for each object planned after its
deadline (`render` repeats it on standard error). `validate` does not judge it. A View
can draw it (`deadlines: {show: slipped}`: a tick at the date and a run to the planned
finish), and a terse plan states it with a last clause, `deadline 2027-06-30`.

## Install and refresh this skill

This skill ships inside the chrona package, so it always matches the installed command.
`chrona skill copy` copies it into an empty or absent directory and refuses to
overwrite anything. Point it at the skills directory your agent host reads (for example
`.claude/skills/chrona`):

```bash
chrona skill copy --output agent-skills/chrona
```

After upgrading chrona, refresh by copying into a new directory, comparing it with the
installed one (`diff -r` on macOS and Linux), and replacing the old directory with the
new one. A failing copy writes nothing: `E_SKILL_OUTPUT_EXISTS` means the directory is
not empty, so choose a new one.

## Where the rules live

This skill teaches the workflow, not the specification. Spec 05 (project format), Spec 04
(scheduling) and Specs 06, 07 and 33 (view, theme, layout) in `docs/specification/` of the
chrona repository state the rules; the skill links to them instead of restating them.

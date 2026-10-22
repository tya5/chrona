# Diagnostics an agent meets on the draft path

Read `code` and `sourceRef` first; `sourceRef` is a JSON pointer into the file you
edited (`/objects/design/schedule` is `objects: design: schedule:`) or a relation id
(`/relations/build-to-launch`). Errors are printed as one JSON object on standard output:

```json
{"status": "rejected", "diagnostics": [{"code": "E_REFERENCE", "severity": "error", "component": "core", "sourceRef": "/relations/0/to/object", "revisionRefs": [], "message": "Unknown to object"}]}
```

Every row has a `message` that says what is wrong. A row may also carry `count` (2 or
more): equal findings were merged into it; no `count` means it happened once.

Exit status: 1 for `rejected` (the plan or a preset is wrong), 2 for `failed` (the file,
the flag or the output suffix is wrong), 0 for success. Successful `render`,
`render-review` and `render-workspace` print one JSON stdout envelope
`{"status": "ok", "diagnostics": [], "warnings": [...]}`. Read `warnings`
there, not former stderr JSON lines; warnings and notes keep exit 0.

Every code below is checked by a test against the source, and each plan-level code is
provoked by the test with a small synthetic plan, so a removed or renamed code fails the
build. Over MCP the codes the tools, guided authoring and Store commands add follow the tables
below in the same resource. Codes neither lists exist; if you meet one, quote it to the
user and do not guess a fix.

## Plan errors (validate, schedule, render)

| Code | Command that emits it | What it means | What to change |
| --- | --- | --- | --- |
| `E_SCHEMA` | `validate`, `schedule` | The plan's structure is wrong at `sourceRef`. For `/objects/<id>/schedule` the message lists the permitted forms by `mode`; if it omits `scheduled` while your object has an `amount`, the `amount` is invalid. | Fix the first `sourceRef`: a `mode` that is not `fixed-point` (`at`), `scheduled-point` (no date), `fixed-span` (`start`, `end`), `scheduled` (`amount`) or `rollup`, or an `amount` that is not `Nwd` with a positive whole `N`. A file that is empty or a YAML list is also `E_SCHEMA` at `/`: a plan is a mapping with `version`, `project` and `objects`. |
| `E_PROJECT_SCHEMA` | `render` | The same structural error as `E_SCHEMA`, reported by `render`. | Same as `E_SCHEMA`; `component` is `closure`. |
| `E_REFERENCE` | all three | An id names nothing: a relation endpoint object, an object `calendar`. | Correct the id at `sourceRef` or add the missing object or calendar. |
| `E_ENDPOINT_MODE_MISMATCH` | all three | A relation uses an endpoint the object's schedule does not have: a gate has `at`, not `start`. | Use `at` for a `fixed-point` or `scheduled-point` object and `start` or `end` for a span. |
| `E_INVALID_SPAN` | all three | A `fixed-span` has `start` not before `end`. | Make `start` earlier than `end` (`end` is exclusive). |
| `E_CALENDAR_REQUIRED` | all three | A `wd` amount has no calendar. | Add `calendar:` to the object or `project.calendar`, and define it under `calendars`. |
| `E_UNSUPPORTED_CYCLE` | all three | The relations form a cycle, so no schedule exists. The message lists the objects on it and `sourceRef` is the relation that closes it. | Remove or redirect one relation in the cycle, then run `validate` again. |
| `E_UNSATISFIABLE_DEPENDENCIES` | all three | A cycle whose positive lags can never be met: the same finding as `E_UNSUPPORTED_CYCLE`, with a stronger cause. | Remove or redirect one relation in the cycle at `sourceRef`. |
| `E_FIXED_TARGET_VIOLATION` | `schedule`, `render` (not `validate`) | A `fixed-point` or `fixed-span` object sits earlier than its predecessors allow; `sourceRef` is the relation. | Write the date the message names, or for a gate drop the date and use `scheduled-point`; or shorten the work before it, or loosen the relation. |
| `E_CONTRADICTORY_BOUNDS` | `schedule`, `render` (not `validate`) | A `constraints` bound on `sourceRef` cannot be met by the dependencies (for a `scheduled-point`, `constraints.at.max`). It often comes with `E_FIXED_TARGET_VIOLATION`. | Relax the bound or move the work that pushes it. |

## Command and input errors (exit 2, or 1 for a preset)

| Code | What it means | What to change |
| --- | --- | --- |
| `E_INPUT_IO` | A file you named does not exist or cannot be read. | Fix the path; not a plan problem. |
| `E_INPUT_YAML` | The file is not valid YAML; the message has the line and column. | Fix the YAML syntax at that line. |
| `E_COMMAND_SYNTAX` | A flag is missing or wrong (`render` always needs `--output`; `validate` needs a project path). | Re-run with the flags `chrona <command> --help` lists. |
| `E_RENDER_OUTPUT_EXTENSION` | The `--output` suffix is not one of `.svg`, `.png`, `.pdf`, `.typ`, `.tex` or none. | Use `.svg` or `.png`. |
| `E_RENDER_OUTPUT_FORMAT_MISMATCH` | `--format` disagrees with the `--output` suffix. | Drop `--format`, or make the suffix match. |
| `E_RENDER_RASTERIZER_UNAVAILABLE` | A `.png` or `.pdf` render needs the `render` extra, which is not installed. | `pip install 'chrona[render]'`, or write `.svg`. |
| `E_BUILTIN_PRESET_UNKNOWN` | `--preset` is neither a path nor a builtin id. The message names the value you passed and lists every valid id. | Run `chrona preset list` and use one of its ids, or pass a path to a `preset.yaml`. |
| `E_BUILTIN_PRESET_OUTPUT_EXISTS` | `chrona preset copy --output DIR` found `DIR` already in use. | Copy to a new directory; do not overwrite. |
| `E_BUILTIN_PRESET_NEW_ID` | `chrona preset copy --id NAME` got a name outside the copied resources' identifier contract. | Use 1–256 characters: start with a letter, then use letters, digits, `.`, `_` or `-`. |
| `E_INIT_OUTPUT_EXISTS` | `chrona init DIR` found `DIR` already in use. | Pick a new directory name. |
| `E_SKILL_OUTPUT_EXISTS` | `chrona skill copy --output DIR` found `DIR` already in use. | Copy to a new directory; do not overwrite. |
| `E_RESOURCE_VERSION_UNSUPPORTED` | A preset copied by an older chrona is stale for this version. | Copy the preset again into a new directory and re-apply your edits. |

## Forecast and baseline comparison (`render --forecast`, `--snapshot`)

Every code the forecast path can emit. An object the `--snapshot` baseline does not contain is
new: it draws normally, its baseline delta cell reads `new`, and the forecast skips its baseline
comparison. A baseline object the current plan no longer has is removed: it draws as a baseline
ghost row titled `... (removed)`, or, when the View shows no ghosts, is listed by `I_BASELINE_OBJECT_REMOVED`.

| Code | Severity | What it means | What to change |
| --- | --- | --- | --- |
| `E_FORECAST_BASELINE_UNAVAILABLE` | error (exit 1) | A displayed object has no forecast schedule, or the baseline holds it as a different kind (span versus point). An object merely missing from the baseline is new, not this error. The message names the object and the cause. | Make the object schedulable, or pass a Snapshot in which it has the same kind. |
| `E_FORECAST_PRESENTATION_REQUIRED` | error | An explicit-rows View shows a forecast object without a Snapshot track. | Add a `snapshot` item for that object to its row. |
| `E_FIXED_TARGET_VIOLATION` | info in a forecast | A fixed date sits before what its predecessors now allow. | Tell the user; nothing was moved. |
| `I_FORECAST_MOVED`, `I_FORECAST_START_UNOBSERVED`, `I_FORECAST_ROLLUP_OBSERVATION_CONFLICT` | info | Counts and notes about the forecast itself. | None. |
| `I_BASELINE_OBJECT_REMOVED` | info | Baseline objects that the current plan no longer has, and that no ghost row shows (the View hides ghosts, or its rows are explicit). `objects` lists their ids and titles. | Tell the user which tasks were removed; use `comparison.baselineMarks: ghost` to draw them. |

## Warnings and notes (render succeeded, exit 0, in stdout.warnings)

A warning has a `message` (what happened, then which label or placement) and its measured
facts. Object-backed warnings name the known Project title and its escaped
`/objects/<id>` pointer; axis, slot, relation and other non-object findings do
not invent an object. Warnings with the same code and cause are one row: `count` says how many (2 or
more), the first subject is in `message` and `diagnostic`, and `occurrences` lists the
others (at most 20). The picture is written; the question is whether you accept it.

| Code | What it means | What to do |
| --- | --- | --- |
| `W_LAYOUT_LABEL_SUPPRESSED` | A label did not fit and was left out of the picture. | Shorten the title, or widen `--viewport`. |
| `W_LAYOUT_ROUTING_COST` | At least 2,370 potential normal-stage connector-port pairs were prepared, before expensive routing. This conservative work bound covers the measured trial9 150-task target-b and 240-task default cases; `potentialPortPairs` is not evaluated searches or a time promise. Policy, hints, blockers and retries affect actual cost. | Explicitly omit drawn relations with `--relations none`, or review the Layout Profile `relationRouting` policy. No dependency is removed automatically. |
| `W_LAYOUT_LABEL_OVERFLOW` | A label does not fit its space (for example `label-collision` on the time axis) and is drawn overflowing. | Widen `--viewport` or shorten the text; a very small viewport (like `300x200`) causes it. |
| `W_SCENE_TEXT_INTERSECTION` | Two pieces of text overlap in the drawn scene. | Widen `--viewport` or shorten the labels; look at the picture before accepting it. |
| `W_SCENE_MARK_CONTRAST`, `W_SCENE_STATE_TEXT_CONTRAST`, `W_SCENE_CONTRAST_GROUND_UNSUPPORTED` | A mark or text is fainter than its contrast floor (3:1 for a mark, 4.5:1 or 3:1 for text) against what it lies on, or lies on a ground whose colour cannot be computed. The theme did not ask for contrast to be enforced, so this is a warning, not an error. | Accept it if it reads well; otherwise darken the ink or change the ground. A theme that wants it enforced sets `contrastPolicy: {mark: error, stateText: error, groundText: error}` (`none` silences a class). |
| `W_SCENE_CONTRAST_ACCEPTED` | A pair below its contrast floor that the theme's `contrastPolicy.exceptions` entry accepts: its measured ratio is at or above the entry's `minimum`. The warning records the ratio, the floor, the minimum and the reason. | Nothing, if the reason still holds; a pair below the `minimum` is still an error. |
| `W_SCENE_CONTRAST_EXCEPTION_UNUSED` | A `contrastPolicy.exceptions` entry matched no pair that needed it (its class is not `error`, or no pair has that role or purpose over that ground). | Fix the entry's `role`, `purpose` or `over`, or delete it. |
| `W_SCENE_DECORATION_CONTRAST` | A background decoration (a stripe, band or tint) is fainter than its 1.10:1 floor against what it lies on. Marks and text are not covered: those below their floor are errors in the project's own gate. | Accept it if the faint shading is the design; otherwise strengthen the band colour or opacity. |
| `W_SCENE_DECORATION_GROUND_UNSUPPORTED` | A background decoration lies on a translucent ground, so its contrast cannot be measured. Text and marks on a translucent chip or panel are not covered: they are judged on the colour it makes over what lies beneath it. | Accept it, or paint the band over an opaque one. |
| `W_LAYOUT_*` | Other layout adaptations (a label thinned, a relation suppressed). | Same: widen `--viewport` or simplify; accept if the picture reads. |
| `W_FONT_*` | A font feature was unavailable or a glyph was substituted. | Accept, or choose a different preset; do not change fonts unless asked. |
| `W_VIEWER_FIT_NOT_HONOURED` | `.typ` or `.tex` output of a preset that declares a viewer-fit mode for a box role (`sunday`, `target-b`, `titlecard`, `yuya`): Typst and TikZ cannot pin a text run to its box, so that role is drawn plain, as in `.svg` without the fit. The `message` names the role. | Nothing; the picture is complete. Render `.svg`, `.png` or `.pdf` (where the fit is applied or does not matter), or use another preset, for no warning. |
| `W_DEADLINE` | An object is planned to finish after its `deadline`. Unlike the rows above it has a `message` and `details` (`object`, `endpoint`, `finish`, `deadline`, `daysLate`), and `chrona schedule` lists it under `warnings` as well. | Tell the user the days late; move the plan or the deadline only if asked. It is a promise, not a bound: nothing was moved. |
| `I_LAYOUT_PLOT_LABELS_SUPPRESSED` | A note: plot labels were dropped because they would not fit. | None; widen `--viewport` if you need them. |

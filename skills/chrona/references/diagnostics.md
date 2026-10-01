# Diagnostics an agent meets on the draft path

Read `code` and `sourceRef` first; `sourceRef` is a JSON pointer into the file you
edited (`/objects/design/schedule` is `objects: design: schedule:`) or a relation id
(`/relations/build-to-launch`). Errors are printed as one JSON object on standard output:

```json
{"status": "rejected", "diagnostics": [{"code": "E_REFERENCE", "severity": "error", "component": "core", "sourceRef": "/relations/0/to/object", "revisionRefs": [], "message": "Unknown to object"}]}
```

Exit status: 1 for `rejected` (the plan or a preset is wrong), 2 for `failed` (the file,
the flag or the output suffix is wrong), 0 for success. Warnings and notes are JSON lines
on standard error and the exit status stays 0.

Every code below is checked by a test against the source, and each plan-level code is
provoked by the test with a small synthetic plan, so a removed or renamed code fails the
build. Codes this file does not list exist (the full list is `docs/diagnostics/inventory.md`
in the repository); if you meet one, quote it to the user and do not guess a fix.

## Plan errors (validate, schedule, render)

| Code | Command that emits it | What it means | What to change |
| --- | --- | --- | --- |
| `E_SCHEMA` | `validate`, `schedule` | The plan's structure is wrong at `sourceRef`. For `/objects/<id>/schedule` the message lists the permitted forms by `mode`; if it omits `scheduled` while your object has an `amount`, the `amount` is invalid. | Fix the first `sourceRef`: a `mode` that is not `fixed-point` (`at`), `scheduled-point` (no date), `fixed-span` (`start`, `end`), `scheduled` (`amount`) or `rollup`, or an `amount` that is not `Nwd` with a positive whole `N`. |
| `E_PROJECT_SCHEMA` | `render` | The same structural error as `E_SCHEMA`, reported by `render`. | Same as `E_SCHEMA`; `component` is `closure`. |
| `E_REFERENCE` | all three | An id names nothing: a relation endpoint object, an object `calendar`. | Correct the id at `sourceRef` or add the missing object or calendar. |
| `E_ENDPOINT_MODE_MISMATCH` | all three | A relation uses an endpoint the object's schedule does not have: a gate has `at`, not `start`. | Use `at` for a `fixed-point` or `scheduled-point` object and `start` or `end` for a span. |
| `E_INVALID_SPAN` | all three | A `fixed-span` has `start` not before `end`. | Make `start` earlier than `end` (`end` is exclusive). |
| `E_CALENDAR_REQUIRED` | all three | A `wd` amount has no calendar. | Add `calendar:` to the object or `project.calendar`, and define it under `calendars`. |
| `E_UNSUPPORTED_CYCLE` | `schedule`, `render` (not `validate`) | The relations form a cycle, so no schedule exists. `validate` prints `[]` for a cycle. | Remove or redirect one relation in the cycle named at `sourceRef`, then run `schedule`. |
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
| `E_BUILTIN_PRESET_UNKNOWN` | `--preset` is neither a path nor a builtin id. The message is only the code. | Run `chrona preset list` and use one of its ids, or pass a path to a `preset.yaml`. |
| `E_BUILTIN_PRESET_OUTPUT_EXISTS` | `chrona preset copy --output DIR` found `DIR` already in use. | Copy to a new directory; do not overwrite. |
| `E_INIT_OUTPUT_EXISTS` | `chrona init DIR` found `DIR` already in use. | Pick a new directory name. |
| `E_SKILL_OUTPUT_EXISTS` | `chrona skill copy --output DIR` found `DIR` already in use. | Copy to a new directory; do not overwrite. |
| `E_RESOURCE_VERSION_UNSUPPORTED` | A preset copied by an older chrona is stale for this version. | Copy the preset again into a new directory and re-apply your edits. |

## Warnings and notes (render succeeded, exit 0, on standard error)

A warning has no `message`, only its code and measured facts. The picture is written; the
question is whether you accept it.

| Code | What it means | What to do |
| --- | --- | --- |
| `W_LAYOUT_LABEL_SUPPRESSED` | A label did not fit and was left out of the picture. | Shorten the title, or widen `--viewport`. |
| `W_LAYOUT_LABEL_OVERFLOW` | A label does not fit its space (for example `label-collision` on the time axis) and is drawn overflowing. | Widen `--viewport` or shorten the text; a very small viewport (like `300x200`) causes it. |
| `W_SCENE_TEXT_INTERSECTION` | Two pieces of text overlap in the drawn scene. | Widen `--viewport` or shorten the labels; look at the picture before accepting it. |
| `W_LAYOUT_*` | Other layout adaptations (a label thinned, a relation suppressed). | Same: widen `--viewport` or simplify; accept if the picture reads. |
| `W_FONT_*` | A font feature was unavailable or a glyph was substituted. | Accept, or choose a different preset; do not change fonts unless asked. |
| `W_DEADLINE` | An object is planned to finish after its `deadline`. Unlike the rows above it has a `message` and `details` (`object`, `endpoint`, `finish`, `deadline`, `daysLate`), and `chrona schedule` lists it under `warnings` as well. | Tell the user the days late; move the plan or the deadline only if asked. It is a promise, not a bound: nothing was moved. |
| `I_LAYOUT_PLOT_LABELS_SUPPRESSED` | A note: plot labels were dropped because they would not fit. | None; widen `--viewport` if you need them. |

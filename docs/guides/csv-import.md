# Import a plan from a spreadsheet (CSV or TSV)

`chrona import` turns a table (one row per task, gate or group) into the Chrona Project YAML, and optionally an Actual Set.
Export the sheet as CSV (or TSV) from your spreadsheet or scheduling tool, import it once, then edit the YAML from then on.
Next to the [terse plan card](terse-plan.md): the table is converted to a terse plan and compiled by the same compiler, so the
Project is the one `chrona compile` writes for that plan. XLSX, MS Project XML and live sync are not supported.

## The loop

<!-- chrona:doc-check file: plan.csv -->
```csv
id,title,type,start,end,duration,parent,predecessors,deadline,progress,actual_start,owner
kickoff,Kickoff,gate,2027-03-01,,,,,,,2027-03-01,pm
design,Design,task,2027-03-02,,10wd,,,,60%,2027-03-02,ana
phase-2,Phase 2,group,,,,,,,,,
build,Build,task,,,20wd,phase-2,design +1wd,2027-05-14,0.25,,bo
tests,Tests,task,,,5wd,phase-2,build,,,,
launch,Launch,gate,,,,,"tests +2d, kickoff",2027-06-30,,,
```

```sh
chrona import plan.csv --output project.yaml --actual-output actual.yaml --project-id launch-plan --title "Launch plan" --calendar "standard mon-fri" --as-of 2027-04-01
chrona validate project.yaml
chrona schedule project.yaml
chrona render project.yaml --actual actual.yaml --output plan.svg
```

The import never overwrites a file: delete the target first. Every row problem is reported in one run, each with the row and
column of its cell (the header is row 1). Exit code 1 for a rejected table, 2 for an unreadable file or an existing output.

A spreadsheet that exports with semicolons and your own header names needs a delimiter and a header map:

<!-- chrona:doc-check file: sheet.csv -->
```csv
Task id;Name;From;To
t1;First;2027-03-01;2027-03-05
t2;Second;2027-03-08;2027-03-12
```

<!-- chrona:doc-check file: columns.yaml -->
```yaml
Task id: id
Name: title
From: start
To: end
```

```sh
chrona import sheet.csv --output sheet.yaml --columns columns.yaml --delimiter semicolon
```

## Columns

Headers match case-insensitively; spaces and hyphens read as underscores (`Actual Start` is `actual_start`). The vocabulary is
closed. Only `id` is required.

| Column | Meaning |
| --- | --- |
| `id` | the object id: lower-case letters, digits, hyphens, starting with a letter. Unique |
| `title` | the label (optional) |
| `type` | `task` (default), `gate` or `group` |
| `start` | `YYYY-MM-DD`: a gate's fixed date, or a task's first day |
| `end` | `YYYY-MM-DD`, **exclusive**: the first day after the task |
| `finish` | `YYYY-MM-DD`, **inclusive**: the last day of the task. Use `end` or `finish` as a column, not both |
| `duration` | `5d` (calendar days), `2w`, `20wd` (working days; needs a `--calendar`) |
| `parent` | the id of a `group` row; children are placed under their group |
| `predecessors` | comma-separated ids with an optional endpoint and lag, exactly the terse `after` grammar: `design`, `design.start`, `design +1wd`, `tests +2d, kickoff` |
| `deadline` | `YYYY-MM-DD`; moves nothing, `schedule` warns if it is missed |
| `calendar` | a calendar name declared with `--calendar` |
| `progress` | observed progress: `60%`, `60` or `0.6` (a value above 1 is a percentage). Goes to the Actual Set |
| `actual_start`, `actual_finish` | observed dates, to the Actual Set (for a gate, either one is the observed date) |

A schedule is read from `start`/`end`/`finish`/`duration`: start and end (or finish) give a fixed span, a duration with a start
(or an end) gives a scheduled span, a duration alone relies on `predecessors`, a gate with predecessors and no date is derived
from them, a group takes none. Any other column becomes a text entry in the object's `fields` (`owner` above), and a blank
cell adds nothing. `--columns map.yaml` maps your header names to the vocabulary (`Task name: title`).

## Options

- `--output`, `-o`: the Project YAML (required). `--actual-output`: the Actual Set, required when the table has `progress` or
  `actual_*` values; `--as-of DATE` sets its observation date.
- `--project-id` (default: the file name as a slug) and `--title`.
- `--calendar "NAME DAYS [except DATE ...]"`, repeatable; the first declared calendar is the project default. A table with
  `wd` amounts needs one.
- `--delimiter comma|tab|semicolon`: the default is tab for `.tsv`, comma otherwise.

## What it checks

A bad date, an unknown predecessor, a duplicate id, an unknown `parent`, a parent cycle, a bad `type` or amount: each is a
diagnostic at its cell, with the same codes and hints as the terse compiler (`E_TERSE_*`) or an `E_IMPORT_*` code, and the
generated Project then goes through normal validation.

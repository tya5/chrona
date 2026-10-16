# Issue 1566: the plan-update guide and the skill section

Status: design note, written before the guide. Source of truth: the issue body and the
reviewer comment of 2026-10-15 13:26Z (`gh issue view 1566 --comments`).

## Baseline (published, verified on `origin/main` 355f06066)

- `chrona render --actual A --snapshot B --preset target-b` draws the current plan, the
  actuals, the baseline ghosts (dashed) and a `Δ finish` column. The default preset
  (`chrona-default-draft`) accepts `--snapshot` but draws no ghost and no `Δ finish`
  (checked: its output is byte-identical with and without `--snapshot`), so the guide names
  `--preset target-b`. Spec 06 §4.2: Draft `--snapshot` supplies the Snapshot Project without a
  Store or Context.
- `Δ finish` is the Actual finish minus the **current** plan's finish (Spec 06 §4.2), not
  minus the baseline. The ghost is what shows the move against the baseline.
- An open task is an observation with `start`, `openUntil: asOf` and `progress`; without
  `openUntil` the Actual is incomplete (`W_LAYOUT_ACTUAL_INCOMPLETE`) and its bar is not drawn.
- The Actual `finish` is exclusive, like a plan `end`. A gate uses `at`.
- Docs CI: `tools/check_documented_commands.py --check --execute` (conformance check
  `documented-commands`) validates every `chrona` line of `README.md`, `docs/guides/*.md`,
  `skills/chrona/SKILL.md` and `references/*.md` against the live parser and runs the unmarked
  ones in one disposable workspace. A `<!-- chrona:doc-check file: NAME -->` fence writes a
  file into that workspace (flat names, shared by all documents, so the guide's names are
  prefixed `update-`); non-chrona lines such as `cp` are not run.

## Acceptance rows

| # | Literal row (issue 1566) | Basis | Evidence planned |
| --- | --- | --- | --- |
| 1 | An agent with only the copied skill can do the loop on `skills/chrona/examples/launch.yaml`; the reviewer checks it with a fresh agent session and records the summary on the issue. | Decision 2: the skill carries the loop as one section plus a pointer to the guide. | The section; I ran its commands on `launch.yaml` in a scratch copy. The fresh-agent check is the reviewer's and stays open. |
| 2 | The guide's commands run in docs CI. | Decision 1; `first-project.md` and `csv-import.md` mechanism. | `docs/guides/update-a-plan.md` uses `file:` fences and unmarked `chrona` lines; `--check --execute` run locally. |
| 3 | No "reproducible" selling point remains in the skill. | Issue Problem 3, Decision 2; reviewer comment adds the `render` and `render-review` help strings. | SKILL.md description and body reworded; CLI help, golden, `cli-reference.md`, MCP tool text reworded. |

| 4 | Reviewer addition 2026-10-16 (a): baseline save and next-week comparison via the draft route `render --snapshot <saved project.yaml>` first; `baseline-capture` needs a Store and `--command`. | Outsider trial comment on the issue. | Guide step 1 and skill step 1. |
| 5 | (b): how to record next week's actuals other than hand-editing or CSV re-import. | Same. | Guide "The next update" (append with higher `sequence`, executed in CI); skill step 2. Gap: no draft command writes an observation; `actual-intake` is Store-only and has no step-by-step guide. |
| 6 | (c): the skill mentions `chrona import`. | Same. | Skill section, executed in CI with its own file fence. |

Decision 3 (link from README quick start and `first-project.md`'s last step) and the owner's
requirement that outside users and agents can find it are met by these links: README quick
start and feature list, `first-project.md`, `docs/README.md`, the `chrona init` README
template, the skill description and section (also the MCP resource `chrona://guide/authoring`,
which serves SKILL.md), the MCP server instructions and the `chrona --help` footer.

## Boundaries

- No `examples/**` edit; the guide may link to `examples/chrona-roadmap`.
- Not documented: `identity --update` (#1567 was rescoped; no such command), pinned or
  reproducible evidence. Known gap: the guide does not use a Store; the Store path stays in the
  progressive tutorial.
- One PR, `Refs #1566` only. Bot-generated files are not committed.

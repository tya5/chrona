# Chrona development workflow

This file is the working procedure for repository contributors and coding
agents. It is tool-neutral, and Claude Code and Codex both read it directly.
Follow it for issue work, including fixes and refactors.
The current GitHub `main`, issue text, and published repository documents are
the source of truth; handoff notes and unpushed local work are leads to verify.
Do not rely on any tool's private memory for project state. Anything a
successor needs must be in the repository or on the issue.

## Setup and everyday commands

```bash
python -m venv .venv
.venv/bin/python -m pip install -e '.[dev,render]' -e packages/chrona-fonts-noto-cjk
.venv/bin/python -m pytest -q tests/unit/chrona/presentation/layout/test_presentation_labels.py
.venv/bin/python conformance/run_conformance.py
.venv/bin/python tools/regenerate_public_examples.py --check --jobs 4
```

On Windows, use `.venv\Scripts\python.exe` in place of `.venv/bin/python`.
Create the venv inside the worktree being tested; an editable venv from another
checkout may silently import that checkout instead. Always use that venv.
`CONTRIBUTING.md` has the repository map.

## Choosing and claiming work

- **What to take next:** the pinned issue #454 is the reviewer-maintained
  priority board. Read it; do not edit or close it.
- **Coordinate writes:** before implementing an issue, comment with the tool,
  first slice, and public base. One coordinating owner publishes it; delegated
  read-only or non-overlapping work may use separate worktrees. Check a recent
  claim before taking over. Read-only review needs no claim.
- **Publish serially:** separate worktrees isolate agents, but only one
  coordinated publication to `main` occurs at a time. Fetch and inspect before
  each push or merge; do not rebase a shared/published branch or overwrite an
  unexpected remote update.
- **Reviewer PRs:** compare scope and current design with `main`, resolve
  conflicts, then inspect current CI before merging. A green old-base run alone
  is not acceptance.

## Required sequence

The full sequence applies to semantic, schema, ownership, compatibility, or
cross-module work. For a local defect confined to one owner with no such
change, combine steps 1–4 in the one concise issue work record, then keep the
literal acceptance review. Land an agreed independent slice when possible;
an unresolved contract or layer gap still requires design correction first.

### Fast path for fixes and attribute knobs

Most board items are defect fixes or attribute-level knobs on an existing
mechanism (board depth B or C, or `fix`). They take the fast path unless they
introduce a new layer, ownership boundary, public schema version or
compatibility promise:

- **Plan in the issue, not in `docs/`.** Steps 1–4 are one Status comment on
  the issue of about 20 lines: baseline commit, the literal acceptance rows,
  the rule to implement, the files touched and the tests. Do not add design,
  architecture-review or implementation-plan files under `docs/planning/` or
  `docs/design/` for these items, and do not publish them as separate PRs.
- **One PR per item.** Code, synthetic tests and the specification lines the
  behaviour needs land together. A changed public output is not a reason to
  pre-publish a design: disclose it in the PR body as a short count table
  (per slide: routes, labels or primitives changed, removed or added, and new
  diagnostics). The reviewer or owner accepts or rejects it there.
- **Never absorb a side effect by editing `examples/**`.** Report it with
  counts; the corpus is not an oracle.
- **One active item per session.** Merge, or park with a Status comment,
  before opening the next item's PR.
- **Acceptance stays literal but short.** The acceptance review file keeps one
  row per literal criterion with evidence links; it needs no narrative beyond
  that.

### Merge coordination

There is no repository merge lock. Before the final push, the base must be the
`origin/main` tip whose `derived-main` check run is `completed`/`success`
(`gh api --method GET repos/tya5/chrona/commits/<sha>/check-runs -f check_name=derived-main -f filter=all`).
If `main` advances while checks run, rebase onto the new ready tip and re-run;
never patch generated output. When two sessions are about to merge, the one
merging posts a one-line "Merging #N now" on its issue, and a fix that turns a
red `main` green goes first.

Every landing costs one serial ready-tip cycle (about 15 min of derived sync
plus a re-run of CI), so spend cycles on code, not paperwork:

- **Batch documents.** Literal acceptance reviews, release records and other
  `docs/`-only changes go out as one PR per session per merge window, not one
  PR per issue.
- **Batch small code PRs.** When a session has three or more small, separately
  reviewed and green PRs waiting, land them as one integration PR (each commit
  keeps its own `Refs #N`) instead of one cycle each. Keep a PR separate when it
  touches derived inputs another open PR also touches, or when it is large
  enough that a failure would block the others.
- **Reviewer PRs** (examples, docs) count in the same lane: the dev session
  that lands next brings them to the ready tip and lands them before its own
  next item (board #454, row 1).

1. **Establish the baseline.** Read the issue body and later comments, current
   `main`, active plans, relevant specifications/ADRs, code, tests, and public
   artifacts. Record what is published, what is inferred, and what remains
   unverified. Copy every literal issue acceptance criterion into the work
   plan; identify dependencies and the next independently publishable slice.
2. **Write the design plan.** Define use cases, open decisions, responsibility
   boundaries, data and resource models, migration effects, design review
   questions, acceptance evidence, and the order of design slices. Publish it
   before making design decisions in code.
3. **Complete the design and architecture review.** Specify the selected
   behavior, schema and identity rules, layer connections, failure behavior,
   extension points, and intended incompatibilities. Check the result against
   the whole architecture and adjacent designs, not only the target module.
   Keep core rules project-independent; use existing declared project resources
   for project-specific presentation tuning. Test core rules with synthetic
   fixtures; treat corpus output as evidence against approved design targets,
   not as an oracle or a reason to edit corpus data to pass a render criterion.
   Update the living specification when semantics, ownership, public schemas,
   or compatibility promises change. Publish the design and review before
   implementation planning is treated as final.
   For View, Layout Profile, and Project schemas, apply Spec 56 §3.2:
   behavior-preserving optional properties are added in place without a
   version bump; schema `default` annotations do not implement runtime defaults.
   A live schema references the shared parts in `schemas/` (`common`,
   `vocabulary`, `graphics`; Spec 56 §7) instead of repeating a pattern, enum,
   or drawing shape. A schema change runs
   `python -m tools.schema_equivalence --base-rev origin/main` and records the
   result in its PR; that run fails on an expected-delta entry that outlived its
   merge by more than one schema merge, and `--prune-stale` retires it.
4. **Write the implementation plan.** Split work into slices that can each be
   reviewed, tested, and published. For each slice name the affected files or
   owners, schema and resource migrations, generated evidence, focused tests,
   public materializers, acceptance conditions, and publication boundary.
   Publish this plan before changing product code. Keep it in the same concise
   issue work record unless a distinct normative specification is needed.
5. **Implement the approved slices.** Keep domain intent, View, Theme, Layout,
   Scene, and adapter responsibilities in their declared layers. Layout owns
   completed geometry, text measurement, placement, and routes; Scene carries
   completed primitives and paint relations; adapters serialize them. Prefer
   a structural refactor when it removes mixed ownership. Do not retain
   compatibility behavior that defeats the approved design; document the
   migration impact instead.
6. **Verify and review.** Run focused tests during each slice. Before accepting
   a slice, check conformance and affected public materializers, inspect
   generated SVG/Scene/other evidence as a batch, and compare intended changes
   with the general rule and approved design targets. Byte identity proves only
   that an intended no-behavior-change slice changed nothing; it is not a
   quality bar for a behavior change. Use the repository's CI matrix for the
   full pytest and release gate where the plan specifies it; do not duplicate
   a costly full local run
   without a concrete risk. Review behavior, layer ownership, extension
   points, regressions, and every literal issue acceptance item. A passing test
   alone is not acceptance.
7. **Publish and close.** Commit and publish completed design, implementation
   plan, implementation, and acceptance/review phases as separate coherent
   units. Confirm the remote commit and CI/PR state. Close an issue only after
   its literal acceptance table and required release evidence are complete;
   leave reviewer-maintained boards open unless their owner directs otherwise.

If implementation exposes a missing rule, conflicting contract, or layer
breach, pause that slice. Update the current design, review it against the
whole architecture, amend the implementation plan, and publish those changes
before resuming code. Do not hide a design gap behind a local conditional.

Pre-code publication is required when the discovery changes layer ownership,
public behavior or diagnostics, schema/CLI contracts, migration promises, or
literal acceptance. Internal choices within an approved contract may be made
with code and tests, then recorded in the living issue work record in that
commit. A user-visible candidate order, threshold, or validator failure is
not automatically an internal detail.

## Documentation: when, where, and what

Write design and review records in English. Prefer one concise, living issue
work record in `docs/planning/active/` for the baseline, design plan, design,
architecture review, implementation plan, and progress. Update it in place as
the current decision changes; Git history is sufficient for superseded text.
Keep only the latest actionable rule, decision, status, and evidence; do not
append chronological status logs or restate the same contract in several files.
Separate architecture-critical acceptance from local polish; track optional
local tuning in a successor issue instead of expanding the current work record.
Do not create a new plan, correction, amendment, or review file for every
small slice. Keep normative behavior in the relevant living specification,
not duplicated across issue records. Use a separate ADR only when an enduring
cross-cutting decision genuinely needs one. Existing historical files may
remain, but link one current authority instead of repeating their contents.

| When | Location | Record |
| --- | --- | --- |
| Before design | `docs/planning/active/` | Start or update one issue work record: published baseline, literal acceptance, dependencies, questions, slices, and evidence needed. |
| During design, before code | Same issue work record | Current use cases, contracts, ownership, migration, diagnostics, exact behavior, and whole-architecture review. Edit superseded decisions in place; Git retains history. |
| When changing normative behavior | `docs/specification/` (or an ADR only if needed) | Update the relevant living specification and migration impact. The issue record points to it without copying the rule. |
| Before implementation | Same issue work record | Current slice order, owned files, tests, generated outputs, acceptance gates, and publication units. Update this section after a design correction. |
| During implementation | Code, `schemas/`, `conformance/`, `tests/`, `examples/`, `tools/` as applicable | Implement only the approved slice. Commit generated resource mirrors and evidence with their source changes, after checking byte identity and unintended diffs. Record a newly discovered design problem in the design/review/plan locations above before proceeding. |
| At issue release | `docs/reviews/current/` | One concise acceptance review with exact commit, CI/PR links, artifact diffs, architectural findings, and a row for **every literal issue acceptance criterion** (`met`, `deferred`, or `not met`) with direct evidence. A deferred criterion keeps the issue open unless an explicit successor disposition is approved. Slice evidence may be added to the living issue work record without a new review file. |

Keep active plans under `docs/planning/active/` while they are the working
record. Archive completed issue records as described below; legacy files may
remain until separately reviewed. Do not mistake an `Accepted` heading or an
old green run for proof that the current public artifact meets the criterion.
Check rendered output when the criterion concerns what a user sees; Scene-only
evidence cannot prove adapter output is correct.

## Archiving plans and reviews

After an issue's acceptance review, closing comment, and exact-main CI are
complete, archive its issue work record and review in a separate publication:
`docs/planning/active/` → `docs/archive/planning/`, and
`docs/reviews/current/` → `docs/archive/reviews/`. Move legacy per-phase files
for that issue too. Do not move current specifications, decisions, designs,
templates, or ledgers referenced by tools; archive a multi-issue record only
when every issue it covers is closed. Use `git mv`, repair relative links in
the same commit, and run conformance. Link issue/PR evidence to a commit
permalink, not a moving `main` path. Historical backlog migration is separate
work, not a prerequisite for current issues.

The root `.ignore` keeps `docs/archive/` out of default ripgrep results; git
still tracks it. Search history explicitly with `rg PATTERN docs/archive/` or
`rg --no-ignore PATTERN` for rationale, regressions, reopenings, or link fixes.
Archived records are evidence, not current design authority.

## Publication and CI discipline

CI treats derived evidence as a generated snapshot, not PR-authored output.
Every PR first rejects edits to manifest-declared Scene/SVG and report paths,
then generates one disposable snapshot and uploads bounded before/after
evidence. Conformance, code-PR pytest shards, and newest-Python materializer
reproduction consume that same snapshot. Docs-only PRs run conformance without
pytest shards; code PRs run three Ubuntu shards. Fork PR jobs remain read-only.

Each push to `main` enters one non-cancelling serialized sync. It checks out
the latest `main` after acquiring the lock, regenerates the manifest-derived
outputs and reports, and retires only previously tracked generated SVG/Scene
paths no longer declared by manifests. It prepares one bot commit or a no-op,
pushes an immutable `derived-gate/<sha>` ref, dispatches the trusted gate on
that exact SHA, and waits for successful `derived-main` and `derived-ready`
checks before fast-forwarding `main`. The gate also posts `derived-ready` as a
commit status on that exact SHA: a protected branch's push hook does not count
a check run created by a dispatched workflow, but it counts a status. A non-fast-forward or failed gate stops
publication; never patch generated output manually. After publication the
sync dispatches the full three-OS pytest/conformance/wheel-smoke run on the
same immutable ref and SHA. Main pushes do not run that matrix on the stale
pre-sync source SHA. No-op syncs use the existing main SHA for both checks.

After consuming a terminal trusted gate result and dispatching release CI when
the sync succeeds, the sync removes its immutable gate ref. A daily sweep uses
the same non-cancelling, multi-pending concurrency queue. Cleanup preserves
unknown or active gates and never changes commit check runs or release evidence;
an already-absent ref is harmless. Release checkout uses the dispatched SHA.

The `derived-ready` PR check waits (boundedly) for `derived-main` on the
current exact `main` tip and rechecks that tip before success. Production
status-only strict branch protection is a separate deployment step: do not
claim that failed syncs block merges until the Actions check source and bot
fast-forward route have been proven on a disposable protected branch and the
required check has actually been configured. PR speed is not release
acceptance: close an issue only after citing the three-OS run on the exact
published commit containing its acceptance review.

- Before each push, fetch `origin/main`; inspect ahead/behind state, exact
  target commits, staged diff, generated output, and conflict risk. Publish
  serially. Never force-push `main`, reset away others' work, or overwrite an
  unexpected remote update. Stop and reconcile a non-fast-forward or conflict.
- After publishing, verify the remote commit or PR/merge state and state the
  next phase's public base. Do not count unpushed local files as completed.
- Use a project virtual environment for Python packages. Run focused tests
  locally and let CI supply the planned three-OS full pytest/conformance,
  wheel/smoke, and newest-Python public-materializer evidence. Inspect a CI
  run after a material push or expected completion; avoid frequent polling.
- **Test timing data.** `.test_durations` (repository root) records per-test
  durations. The `pr-pytest` shards read it through pytest-split
  (`--splitting-algorithm least_duration`) so the three shards finish together;
  a stale or missing entry costs only balance, never correctness (an unknown
  test gets the average). `.github/workflows/test-durations.yml` refreshes it
  every Monday (05:00 UTC) and on `workflow_dispatch`: it runs
  `pytest -n 4 --store-durations --clean-durations` on an Ubuntu runner and
  opens or updates the pull request `Refresh .test_durations (I657-4)`, which
  is reviewed and merged like any other. To refresh by hand, run the same
  command from a clean checkout and commit only `.test_durations`; do not
  generate it on a loaded machine, because its numbers must describe the CI
  runner. A test marked `corpus` (a whole-corpus or HALCYON-board sweep that has
  a synthetic PR-path twin for its rule) is deselected from the PR shards with
  `-m "not corpus"` and runs in the three-OS full matrix, the nightly run and
  manual dispatch; mark a test `corpus` only together with that twin, never as
  the only PR-path test of a rule.
- If CI is red, identify every failing check from the run, distinguish changes
  introduced by the slice from independent failures, and record the disposition
  before declaring release acceptance. Do not close a ticket while its required
  release gate or user-visible acceptance remains unverified. In particular,
  wait for CI on the exact `main` commit that publishes the issue's acceptance
  review, and cite that run when closing; an earlier implementation-PR run is
  not a substitute.
- Use `Refs #n` rather than closing keywords in partial commits and PRs.
  GitHub can close an issue when such a commit reaches `main`; close it
  deliberately after the literal acceptance review and release gate. This
  covers PR **titles** and **every commit message** (subject and body) a PR
  carries: GitHub reads a merged PR's title like its body, and reads commit
  messages that reach `main` too. When explaining an earlier accident, write the
  issue number without `#`. The `pr-title` check rejects `close|fix|resolve`
  (any tense) followed by `#n` in the title or any commit message unless the PR
  carries the `closes-issue` label.

## Handing off and resuming

Before transferring an unfinished issue or stopping mid-slice, publish
completed units and push your own unfinished work to
`wip/issue-<n>-<topic>`; leave other contributors' changes untouched. Post a
short status block on the issue:

   ```text
   Status (<tool>, <UTC time>)
   Public base: <main commit>; WIP: <branch/commit or none>
   Done: <published units and commits>
   Next: <plan link and first concrete step>
   Risks: <unverified facts or blockers>
   ```

The resumer verifies the named commits/branch against `origin/main`, then
reads the issue and current design. The status block is a lead, not proof;
tool-private memory is not a state store.

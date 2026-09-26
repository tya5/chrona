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
python -m venv .venv && . .venv/bin/activate
python -m pip install -e '.[dev,render]'
python -m pytest -q tests/<focused path>          # during a slice
python conformance/run_conformance.py             # before accepting a slice
python tools/materialize_example.py <manifest> --slide <id> --output <dir>   # public evidence
```

Always run Python through the project environment. A different interpreter on
`PATH` silently tests another checkout. `CONTRIBUTING.md` has the repository
map.

## Choosing and claiming work

- **What to take next:** the pinned issue #454 is the reviewer-maintained
  priority board. Read it; do not edit or close it.
- **Claim before you start:** comment on the issue with the tool (Claude Code
  or Codex), the intended first slice, and the public base commit. Two agents
  never work on the same issue at once. If an issue carries a claim newer than
  a few hours with no later status, ask the owner before taking it.
- **Parallel agents:** each agent works in its own worktree and on a
  different issue. Only one agent pushes to `main` at a time: fetch, rebase
  and verify immediately before each push, and stop on any unexpected remote
  change.
- **Reviewer pull requests:** the reviewer publishes YAML and documentation
  changes as pull requests that reference an issue. They are independent of
  in-flight code work unless the PR says otherwise. Merge one after its CI
  passes and its scope matches the PR description. Post-review findings arrive
  as new issues, not as edits to closed ones.

## Required sequence

The full sequence below is for work that changes semantics, public schemas,
layer ownership or compatibility, or that spans several modules. **For a
local defect**, meaning one owner module with no schema, specification or
compatibility change and a fix that is obvious once the cause is known,
combine steps 1–4 into a single short plan document and keep step 6's
literal acceptance review. Prefer landing an independently useful slice
over refining a large design for hours without code. If a design has gone
through several published corrections without a slice landing, stop, publish
the smallest slice that is already agreed, and continue from it.

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
   Update the living specification or record an ADR when semantics, ownership,
   public schemas, or compatibility promises change. Publish the design and
   review before implementation planning is treated as final.
4. **Write the implementation plan.** Split work into slices that can each be
   reviewed, tested, and published. For each slice name the affected files or
   owners, schema and resource migrations, generated evidence, focused tests,
   public materializers, acceptance conditions, and publication boundary.
   Publish this plan before changing product code.
5. **Implement the approved slices.** Keep domain intent, View, Theme, Layout,
   Scene, and adapter responsibilities in their declared layers. Layout owns
   completed geometry, text measurement, placement, and routes; Scene carries
   completed primitives and paint relations; adapters serialize them. Prefer
   a structural refactor when it removes mixed ownership. Do not retain
   compatibility behavior that defeats the approved design; document the
   migration impact instead.
6. **Verify and review.** Run focused tests during each slice. Before accepting
   a slice, check conformance and affected public materializers, inspect
   generated SVG/Scene/other evidence as a batch, and compare intended byte
   changes. Use the repository's CI matrix for the full pytest and release
   gate where the plan specifies it; do not duplicate a costly full local run
   without a concrete risk. Review behavior, layer ownership, extension
   points, regressions, and every literal issue acceptance item. A passing test
   alone is not acceptance.
7. **Publish and close.** Commit and publish completed design, implementation
   plan, implementation, and acceptance/review phases as separate coherent
   units. Confirm the remote commit and CI/PR state. Close an issue only after
   its literal acceptance table and required release evidence are complete;
   leave reviewer-maintained boards open unless their owner directs otherwise.

If implementation exposes a missing rule, conflicting contract, or layer
breach, pause that slice. Write a design correction, review it against the
whole architecture, amend the implementation plan, and publish those documents
before resuming code. Do not hide a design gap behind a local conditional.

## Documentation: when, where, and what

Write design and review records in English. Use descriptive filenames with an
issue number, topic, document type, and date (`YYYY-MM-DD`); link predecessor
and successor documents so a fresh contributor can reconstruct the decision.

| When | Location | Record |
| --- | --- | --- |
| Before design | `docs/planning/active/` | `issue-<n>-<topic>-design-plan-<date>.md`: published baseline, literal acceptance, dependencies, questions, slices, and evidence needed. |
| During design, before code | `docs/design/` | `issue-<n>-<topic>-design-<date>.md`: use cases, contracts, ownership, alternatives, migration, diagnostics, and exact behavior. Use a `-correction-` or `-amendment-` document for later changes; do not silently rewrite history. |
| At design completion | `docs/reviews/current/` | `issue-<n>-<topic>-architecture-review-<date>.md`: explicit consistency check against specifications, ADRs, related designs, and layer boundaries; decision, risks, and unresolved items. |
| When changing normative behavior | `docs/specification/` and/or `docs/decisions/` | Update the relevant living specification or add an ADR with the decision and supersession/migration impact. Design notes alone do not replace normative authority. |
| Before implementation | `docs/planning/active/` | `issue-<n>-<topic>-implementation-plan-<date>.md`: slice order, owned files, tests, generated outputs, acceptance gates, and publication units. Add an implementation amendment after a design correction. |
| During implementation | Code, `schemas/`, `conformance/`, `tests/`, `examples/`, `tools/` as applicable | Implement only the approved slice. Commit generated resource mirrors and evidence with their source changes, after checking byte identity and unintended diffs. Record a newly discovered design problem in the design/review/plan locations above before proceeding. |
| At each slice or issue release | `docs/reviews/current/` | Implementation or acceptance review with exact commit, commands, CI run/PR links, artifact diffs, architectural findings, and a row for **every literal issue acceptance criterion** (`met`, `deferred`, or `not met`) with direct evidence. Use `docs/reviews/issue-acceptance-review-template.md` where appropriate. A deferred criterion keeps the issue open unless an explicit successor disposition is approved. |

Keep active plans under `docs/planning/active/` while they are the working
record; archive them as described below, so that `active/` and
`docs/reviews/current/` list only work in flight. Do not mistake a document's `Accepted` heading or an old green run for
proof that the current public artifact meets an issue's criteria. Check actual
rendered output when the criterion concerns what a user sees; a Scene-only
report cannot prove adapter output is correct.

## Archiving plans and reviews

`docs/planning/active/` and `docs/reviews/current/` must show what is in
flight. Everything else goes to the existing archive.

| | Rule |
| --- | --- |
| **When** | In a separate publication **after** the issue is closed: its acceptance review is published, the closing comment is posted, and CI is green. Never in the same commit as the acceptance review, because the closing comment links to that commit. A plan that is abandoned or fully superseded without its issue closing is archived when a successor document says so. |
| **What** | Every `issue-<n>-*` file of the closed issue in `docs/planning/active/`: design plans, implementation plans, amendments. Every `issue-<n>-*` file in `docs/reviews/current/`: architecture, implementation and acceptance reviews. For a multi-issue programme document, archive it when **all** of its issues are closed. |
| **Where** | `docs/planning/active/<file>` → `docs/archive/planning/<file>`. `docs/reviews/current/<file>` → `docs/archive/reviews/<file>`. Keep the filename; the date in it keeps the history ordered. |
| **Not archived** | `docs/design/` (decision records), `docs/specification/`, `docs/decisions/`, templates such as `docs/reviews/issue-acceptance-review-template.md`, and living ledgers that tools reference by path, e.g. `docs/planning/active/milestone-status-ledger-v0.1.md` in `conformance/validate_design_recompletion.py`. Move a ledger only together with the tool that references it. |
| **How** | `git mv` the files. In the same commit, update every relative link that points to them from documents that stay: an archived review linking `../../planning/active/x.md` becomes `../planning/x.md`, and a current document linking to an archived one points into `docs/archive/`. Then run `python conformance/run_conformance.py`. The literal-acceptance gate scans `docs/reviews/current/` and resolves local links, so a missed link fails it. |
| **Links from issues and PRs** | Link documents by commit permalink (`/blob/<sha>/docs/...`), never by `/blob/main/...`, so that archiving never breaks an issue's evidence trail. |

### The archive is history, and it is search-ignored

`docs/archive/` is not current authority. Do not cite an archived plan or review as the rule for new work. The current rule is in `docs/specification/`, `docs/decisions/`, `docs/design/` and the active plans.

To keep old and rejected designs out of everyday context, the repository-root file `.ignore` lists `docs/archive/`. ripgrep and ripgrep-based code search, including the search in coding agents, skip it in any search that does not name the path. It remains tracked by git and present in every checkout; plain `grep -r` and `git grep` still see it.

Search the archive deliberately when you need it: name the path (`rg <pattern> docs/archive/`, which searches it although it is ignored), use `rg --no-ignore <pattern>` for a whole-repository search, or open the file. Do this when:

- tracing **why** a current rule exists, or which alternatives were rejected, from a link in a current design, specification or ADR;
- **post-reviewing or reopening** a closed issue, whose plans and reviews are archived;
- **archiving** documents or fixing links into `docs/archive/`;
- investigating a **regression** whose earlier fix is recorded there;
- the owner asks about past work.

Do not remove `docs/archive/` from `.ignore` to make it permanently searchable. If a document in it is needed as current authority, move its content into the specification or a current design instead.

The existing backlog is several hundred plans and reviews of closed issues. Archive it once, in its own commit or pull request, following the same rules, before relying on `active/` as a list of open work.

## Publication and CI discipline

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
- If CI is red, identify every failing check from the run, distinguish changes
  introduced by the slice from independent failures, and record the disposition
  before declaring release acceptance. Do not close a ticket while its required
  release gate or user-visible acceptance remains unverified.

## Handing off and resuming

Work may stop at any time, for example when a rate limit ends a session, and
be resumed by another agent or another tool. At every slice boundary, and
before stopping for any reason:

1. Publish completed units. Do not leave finished work unpushed.
2. Put unfinished code on a branch named `wip/issue-<n>-<topic>` and push it,
   or discard it. Never leave uncommitted changes in a shared checkout.
3. Comment on the issue with a status block:

   ```text
   Status (<tool>, <date> <time> UTC)
   Public base: <main commit>   WIP branch: <branch or none>
   Done: <published slices with commits>
   Next: <the next slice, its plan document, first concrete step>
   Open questions / risks: <...>
   ```

A resuming agent reads the issue comments from the newest status block,
checks the named commits and branch against `origin/main`, re-reads the
active plan and design documents, and continues from "Next". It treats the
status block as a lead to verify, not as proof.

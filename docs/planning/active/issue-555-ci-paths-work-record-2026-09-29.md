# Issue #555 — CI paths work record

## Published baseline and design plan

Public `main` at start: `20cf279d6e483da693d7dc803f359d1da8fe854c`.
The current workflow runs conformance, full pytest, and wheel smoke on all
three OSes for every PR and `main` push. PR #484's measured run was about
13 minutes. Issue #526 requires the acceptance-review-bearing `main` commit's
own green CI; #452's throughput design preserves full release evidence.
No product schema, rendering, or materializer bytes change in this issue.

### Literal acceptance

- [ ] A doc-only PR finishes CI in about 3 minutes or less, and still fails when an acceptance review is malformed. Test this with a PR that breaks the review heading.
- [ ] A code PR's CI wall-clock time is at most about half of today's (about 13 min), with pytest sharded on ubuntu, and a failing test in any shard fails the run.
- [ ] Push to `main`, nightly and manual runs still execute the three-OS matrix with conformance, full pytest and wheel smoke. A deliberately OS-specific failure is caught there.
- [ ] `tools/check_ci_outcomes.py` and the independent-outcome reporting work for both paths.
- [ ] `AGENTS.md` describes the two paths, and states that issue closure cites the three-OS `main` run of the acceptance commit.

### Design questions and sequence

The CI workflow owns event routing; a small testable helper owns PR path
classification. Unknown paths or diff failures must select the code path.
Decide the narrow documentation allowlist, deterministic and exhaustive
three-way pytest distribution, independent outcome reporting, and a safe
OS-specific failure probe. Review against #526's exact-main release rule and
the cross-platform release expectations in specifications 62 and 64.

Publish in order: (1) this baseline and design plan; (2) selected design and
whole-architecture review; (3) implementation plan; (4) workflow, helper,
tests, and contributor guidance; (5) acceptance review with live CI evidence.
Each publication uses a separate commit and a checked remote base.

## Selected design and architecture review

`pull_request` runs a classification job against the exact base and head
commits. Only nonempty diffs wholly within `docs/**`, root `AGENTS.md`, root
`README*`, or root `.ignore` take the documentation path; every other path,
rename endpoint, or classification error takes the code path. This fail-closed
allowlist is intentionally narrower than the issue's optional “other non-code
text” phrase. It cannot suppress the workflow itself or its required status.

Documentation PRs run one Ubuntu conformance job and independent outcome
finalization; no pytest or wheel installation/execution. Code PRs run the same
conformance gate, three independent Ubuntu pytest jobs, and the existing
newest-Python materializer reproduction. `pytest-split` assigns every
collected test deterministically to exactly one of three groups; its
`least_duration` algorithm and committed duration data may improve balance
without changing test selection. Each shard uses xdist locally and fails its
own job on a test failure. A skipped/cancelled shard is not success.

`push` to `main`, nightly `schedule`, and `workflow_dispatch` retain the
three-OS matrix, full pytest, and conditional wheel smoke. The newest-Python
job remains. Main runs must neither cancel nor replace each other in
GitHub's one-pending-run concurrency group: group PR runs by PR number, but
give each non-PR run a unique run-ID group. PR runs may cancel older runs of
the same PR. A manual-only, explicit OS-failure probe will exercise
the matrix without committing a broken product test. It is never enabled by
ordinary push or PR events.

This changes CI scheduling, not product semantics: Project → View → Theme →
Layout → Scene → adapter ownership, public schema, resource identity, and
materializer bytes are untouched. Specifications 62 and 64 require the full
release evidence; that remains on `main` and manual/nightly runs. #526's
exact-main acceptance-review run remains mandatory before issue closure.
Risk: shard imbalance or cross-shard fixture coupling may require tuning
after live code-PR evidence; neither permits dropping tests. No normative
product specification or ADR change is needed.

## Implementation plan

1. Add `tools/classify_ci_change.py` and focused tests. Compare exact PR
   base/head with a NUL-delimited, no-rename git diff; include both endpoints
   of renames, and default to `code` on empty/error. Publish with the workflow
   only after the routing test and malformed-review probe are planned.
2. Refactor `.github/workflows/conformance.yml`: PR classifier; Ubuntu-only
   conformance for both PR paths; three Ubuntu pytest-split matrix shards for
   code PRs; retained newest-Python reproduction for code PRs and full events;
   unchanged three-OS full conformance/pytest/wheel jobs for `main`, nightly,
   and manual. Give non-PR runs unique concurrency groups and add a
   manual-only Windows failure probe. Keep independent
   `check_ci_outcomes.py` finalizers and `fail-fast: false`.
3. Add `pytest-split` to dev dependencies, workflow structural and routing
   tests, and `AGENTS.md` path/release guidance. There are no schema/resource
   migrations or generated product artifacts. Local focused tests cover
   classification, outcome reporting, workflow structure, and conformance.
   CI provides full pytest and materializer evidence; compare generated files
   for no product-byte changes.
4. Publish the implementation PR and inspect its Ubuntu code-path runtime
   and shard results. After merge, inspect the exact `main` three-OS run.
   Publish a separate acceptance review, then inspect *that* commit's exact
   `main` three-OS run. Use temporary PR/manual runs to verify a malformed
   review heading, a failing shard, and the OS-specific failure probe; do not
   merge deliberately broken tests or reviews. Close only when every literal
   criterion has direct evidence, else leave open with a precise blocker.

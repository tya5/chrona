# Chrona development workflow

This file is the working procedure for repository contributors and coding
agents. Follow it for issue work, including fixes and refactors. The current
GitHub `main`, issue text, and published repository documents are the source
of truth; handoff notes and unpushed local work are leads to verify.

## Required sequence

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
record. Do not mistake a document's `Accepted` heading or an old green run for
proof that the current public artifact meets an issue's criteria. Check actual
rendered output when the criterion concerns what a user sees; a Scene-only
report cannot prove adapter output is correct.

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

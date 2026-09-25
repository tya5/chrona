# Implementation Plan — Conformance Feedback and Independent CI Execution (#451)

**Design:** `issue-451-conformance-feedback-design-2026-09-26.md`.
**Architecture review:**
`issue-451-conformance-feedback-architecture-review-2026-09-26.md`.

## I451-1 — Deterministic conformance runner protocol

**Files:** `conformance/run_conformance.py`, runner-focused tests/fixtures.

1. Replace first-failure iteration with static `CheckSpec` catalog,
   dependency classification, injectable process/clock seams, bounded capture,
   per-check headers, and stable final summary.
2. Move each existing independent workflow gate into that catalog exactly once;
   preserve profile conformance as a named check.
3. Emit explicit dependent skips and aggregate exit only after all runnable
   checks finish.

**Acceptance:** two induced independent failures both appear; order and exit
are deterministic; dependent check records a reason; no command runs twice.

## I451-2 — Actionable stale derived-artifact reports

**Files:** `tools/derived_artifact_report.py`, five stale producer tools,
focused tool tests.

1. Add byte-preserving compare/diff/report helper with fixed UTF-8/newline
handling and bounded output.
2. Migrate diagnostic, declared-value, vocabulary, presentation-coverage, and
semantic-realization coverage check paths atomically.
3. Preserve fresh `--check` zero exit and no-write behavior; stale reports add
only path, capped diff, refresh argv, and optional Actions annotation.

**Acceptance:** every stale tool exposes its own file/diff/command; fresh
documents remain byte-identical; check mode does not write output.

## I451-3 — Workflow independent-result topology

**Files:** `.github/workflows/conformance.yml`, a small cross-platform Python
outcome helper if needed, workflow structural tests.

1. Set OS matrix `fail-fast: false`.
2. Run conformance and pytest independently after one install using explicit
   continuation; run wheel/install/smoke only after both succeed.
3. Add one always-run outcome aggregation step, with static outcome inputs,
   that makes the job fail after reporting every independent result.
4. Preserve newest-Python materializer job and workflow supersession
   concurrency.

**Acceptance:** static workflow test proves pytest is reached after conformance
failure, peer OS jobs are not cancelled by fail-fast, wheel is skipped with
reason after prerequisite failure, and normal success remains green.

## I451-4 — Evidence and release review

**Files:** generated docs only if a migrated tool detects staleness, CI review
record, no product evidence changes by default.

1. Run focused runner/tool/workflow tests and conformance locally; do not run
   full pytest solely for this CI change.
2. Use one intentionally stale fixture or controlled tool fixture to review
   actual report shape, then restore committed state before publication.
3. Publish the atomic source/workflow change; use three-OS CI to prove full
   pytest, all gates, wheel/smoke, newest-Python reproduction, and independent
   failure visibility.  Query only at expected completion.

**Release acceptance:** every #451 literal acceptance item is demonstrated on
the checked workflow; no validation is omitted or duplicated, and #452 timing
work retains a clear measurement baseline.

## Stop conditions

Return to design if an implementation requires shell-specific control flow,
cross-run cache state, a product-runtime tool import, unbounded logs, an
ambiguous dependency, or a change in individual tool validation semantics.

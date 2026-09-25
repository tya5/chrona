# Design — Conformance Feedback and Independent CI Execution (#451)

**Design plan:** `issue-451-conformance-feedback-design-plan-2026-09-26.md`.
**Status:** Proposed for architecture review.

## Decision

Conformance is a maintainer orchestration boundary, not a product validator.
It executes a finite catalog of independent tool/check commands, captures each
bounded result, prints a deterministic summary, and exits nonzero only after
all runnable checks have reported.  Individual tools preserve their existing
validation authority and exit semantics.

The existing workflow keeps one setup per OS job.  It runs conformance and
pytest as independently reported steps with `continue-on-error`, conditionally
runs wheel/smoke only after both prerequisites pass, and uses one final
cross-platform Python aggregation step to set job failure.  Matrix
`fail-fast: false` ensures an outcome on one OS cannot cancel another.

## Conformance result protocol

`conformance/run_conformance.py` owns immutable internal values:

```text
CheckSpec(id, argv, dependency_class)
CheckResult(id, argv, status, returncode, elapsed_ms, stdout, stderr, skip_reason?)
```

`dependency_class` is either `independent` or names an explicit prerequisite
check.  Every independent spec runs even after a failure.  A dependent spec
whose prerequisite failed becomes `SKIP` with the stable prerequisite id; it
is never silently omitted or executed against invalid input.  The present
tool/profile checks are independent.  Wheel installation/smoke stays outside
this runner because it depends on successful packaging and test/gate results.

The runner captures UTF-8 output with replacement for invalid bytes, bounds
each stream to a documented tail/head-safe maximum, prints a command header
before execution, then prints a stable table ordered by the declared catalog:

```text
CHECK                              STATUS  ELAPSED  DETAIL
diagnostic-inventory               FAIL    0.24s    E_DIAGNOSTIC_INVENTORY_STALE
schema-references                  PASS    0.08s    —
...
```

It exits `1` when any `FAIL` exists and `0` otherwise.  Command argv is
rendered with a platform-neutral structured representation, not shell quoting;
captured output is never environment-dumped.

## Derived artifact diagnostics

`tools/derived_artifact_report.py` is a tool-only shared helper.  A stale
producer provides committed path, regenerated content, stable stale code, and
the canonical refresh argv.  The helper emits:

1. the stable stale code and repository-relative output path;
2. a unified UTF-8 diff capped by line and byte budget, including an explicit
   truncation marker when necessary;
3. the exact refresh command as an argv display;
4. an optional GitHub Actions `::error file=...::` annotation when that
   environment is present.

It does not regenerate/write output during `--check`, change a tool's
comparison bytes, import `chrona`, or turn any stale result into success.  The
five initial stale producers migrate together: diagnostic inventory, declared
value inventory, vocabulary inventory, presentation coverage, and semantic
realization coverage.  Other tools retain their own contracts until explicitly
migrated.

## Workflow topology

Each OS matrix job has this sequence:

```text
install once
  ├─ conformance runner (continue-on-error)
  ├─ pytest -n 4 (continue-on-error; runs regardless of gate result)
  ├─ wheel/build/install/smoke (only if both preceding steps succeeded)
  └─ always-run Python outcome aggregator (fails job if a required result failed)
```

All existing structural and checked derived-output commands move into the
conformance catalog exactly once; this removes duplicate invocations such as
layout-float checking without decreasing coverage.  The newest-Python public
materializer job remains independent.  `fail-fast: false` applies to the OS
matrix; workflow-level concurrency may still cancel superseded commits, never
individual OS jobs within the same commit.

## #452 interaction

#452 may make a tool's within-run parsing/loading efficient, but does not add
cross-run cache state or cause the runner to reuse stale output.  #451 invokes
each logical check once, so it prevents redundant process work while retaining
every check.  Timing facts from `CheckResult` become #452 measurement input;
they are not a performance pass/fail policy.

## Invariants

1. A failure names every failed independent check, including each stale file,
   bounded diff, and refresh argv.
2. Gate failure never prevents pytest reporting in the same OS job.
3. One OS failure never cancels other OS jobs for that commit.
4. Wheel/smoke is explicitly skipped, with reason, rather than attempted after
   invalid prerequisites.
5. Product validation/tool semantics and package import direction do not move
   into the runner or workflow.
6. CI secrets, environment values, and unbounded subprocess output are absent
   from summary/report contracts.

## Required evidence

- runner fixture commands prove two independent failures, one dependent skip,
  command-order determinism, output bounding, and aggregate exit;
- stale-helper fixtures prove byte-identical fresh behavior, bounded diff,
  refresh argv, and no output write in check mode;
- workflow structural tests prove all checks occur once, pytest uses
  `always`/independent continuation, matrix fail-fast is false, and final
  aggregation is cross-platform Python;
- a deliberately stale CI fixture/review demonstrates the final output;
  normal three-OS CI provides release evidence without a duplicate local full
  suite.

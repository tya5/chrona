# Implementation Plan: Deterministic Parallel Pytest CI (#328)

## I328-1 — Reproducible test runner dependency

Add `pytest-xdist` to the existing `dev` extra with a compatible lower bound.
Acceptance: a fresh `pip install -e '.[dev,render]'` supplies the `-n` option;
the package runtime dependencies remain unchanged.

## I328-2 — Workflow concurrency and whole-suite parallelism

Add a workflow/ref concurrency group with `cancel-in-progress: true`. Replace
only the `pytest` command in the existing matrix job with `pytest -n 4`; retain
all gates, wheel build, install, and smoke test steps in their current order.
Acceptance: workflow shape retains both OSes and all non-pytest steps; the
parallel command is explicit and no test is removed or sharded.

## I328-3 — Acceptance

Run serial and `-n 4` full suites, verify identical pass/skip outcomes, run
the public materializer checks, inspect workflow diff, then publish an
acceptance review and close #328. Re-run serial full suite if parallel behavior
exposes state coupling.

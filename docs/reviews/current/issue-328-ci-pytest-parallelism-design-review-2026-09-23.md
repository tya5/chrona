# #328 Deterministic Parallel Pytest CI: Design Review

## Evidence

On the current clean checkout and `.venv`, serial `pytest -q` completed
`420 passed, 7 skipped` in 88.10 seconds. `pytest -n 4 -q` completed the exact
same outcome in 30.21 seconds. The parallel result exercises public CLI,
materializer byte checks, generated SVG checks, and platform-independent
structural tests concurrently; no retry or test exclusion was used.

## Decision

Use a fixed four-worker pytest-xdist invocation in CI. A fixed value is
portable across the Ubuntu and macOS matrix and avoids treating fluctuating
runner CPU counts as part of the test contract. Retain a normal serial local
command; `-n 4` is the explicit parallel verification command.

Add workflow-level concurrency keyed by workflow name and PR/ref, with
`cancel-in-progress: true`. This preserves the latest required evaluation while
discarding obsolete queued/running revisions of the same change. It does not
merge operating-system jobs, skip wheel smoke tests, or cancel another ref.

## Boundary review

| Area | Decision |
| --- | --- |
| Product code | Unchanged; no CI policy enters rendering/scheduling code. |
| Test isolation | Proven by exact full-suite parallel outcome; future shared-state failures require structural isolation, not retries. |
| Dependencies | `pytest-xdist` is a dev dependency, installed reproducibly by existing extras. |
| CI matrix | Both Ubuntu and macOS continue to run all conformance, gates, tests, wheel, and smoke steps. |
| Reproducibility | Full suite remains one command; no shard has weaker coverage. |

## Rejected alternatives

- `-n auto`: runner-dependent worker count makes performance and contention
  nondeterministic across matrix hosts.
- Test sharding: would complicate failure attribution and permit incomplete
  per-job gates.
- Retries for races: hides shared mutable state rather than fixing it.

The implementation may proceed as a single workflow/dependency slice followed
by a CI and materializer acceptance check.

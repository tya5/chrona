# Design Plan — Conformance Feedback and Independent CI Execution (#451)

**Programme:** #454 D454-5.  This is independent design work while #446 waits
for its P0 release gate.

## Objective

Make a failing CI run report all independent conformance failures, actionable
stale-derived-document diffs, test results, and all OS outcomes without
weakening validation or repeating expensive work.  The design must complement
#452 throughput work: execution reuse/caching may improve wall time, but it
must not hide checks or change their authority.

## Current facts to preserve

- `conformance/run_conformance.py` invokes an ordered set of tools and profile
  validation, but exits on its first nonzero command.
- the workflow runs gate steps under default shell failure semantics before
  pytest, and its OS matrix uses default fail-fast behavior.
- stale derived-document tools know both their output path and regeneration
  command, but expose only a bare stable code today.
- wheel build/install/smoke is sequentially dependent on successful package
  construction; it is not an independent check to run after arbitrary failure.

## Design questions

1. Define a typed command-result protocol: stable command id, argv, status,
   captured bounded stdout/stderr, elapsed time, dependency class, and
   deterministic final summary/exit status.
2. Define dependency classification so independent validation runs after a
   failure, while a dependent operation is explicitly skipped with a reason
   rather than executed on invalid prerequisites.
3. Define one reusable stale-artifact report helper that generates bounded
   unified diffs, file identity, exact refresh argv, and optional GitHub
   annotation without importing product runtime code.
4. Decide workflow topology: conformance gates, pytest, and wheel/smoke must
   expose independent results; preserve macOS/Windows execution with
   `fail-fast: false` and avoid duplicating a suite merely to obtain a summary.
5. Establish safe output/privacy bounds and platform-safe command rendering;
   reports must not leak environment/secrets or rely on POSIX-only behavior.
6. Decide whether a single regeneration convenience command is justified only
   after the individual tool contracts share a stable refresh interface.

## Required outputs

- English design with responsibility boundaries, result/skip semantics,
  artifact-diff contract, workflow dependency graph, and #452 interaction;
- architecture review against CI, tools, product import direction, and
  cross-platform behavior;
- implementation plan dividing runner protocol, stale tool integration,
  workflow topology, and release verification into independently reviewable
  publications.

## Verification inputs

- runner fixtures with multiple deliberate independent failures prove all
  commands execute and summary order is deterministic;
- stale fixtures prove bounded diff, output path, and exact refresh command;
- workflow/static tests prove pytest still runs after gate failure and one OS
  failure does not cancel peers;
- focused local runner tests only; remote CI supplies full three-OS and wheel
  evidence once source implementation is published.

## Stop conditions

Return to design if a proposal makes conformance import product runtime,
executes a dependent packaging/smoke action after failed prerequisites,
changes a tool's validation semantics to obtain a diff, or folds #452 caching
into a cross-run stale-state mechanism.

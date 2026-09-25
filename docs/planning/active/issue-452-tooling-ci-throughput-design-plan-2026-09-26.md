# Design Plan — Tooling CI Throughput (#452)

**Status:** planning.
**Trigger:** #452 identifies deterministic, local tooling work that dominates
parallel test-suite wall time without contributing product coverage.

## Public baseline and scope

At the measured public baseline, semantic-registry reachability reparses the
same production tree once per registry identifier.  Coverage tools also use
PyYAML's pure-Python `safe_load` path, and semantic-realization coverage
rediscovers the same corpus for every realization family.  These are tooling
implementation costs, not a reason to weaken tests, cache stale output across
processes, or reduce CI coverage.

The work covers all direct `yaml.safe_load` sites under `tools/`, the
reachability traversal, and within-run corpus discovery/loading in the two
measured coverage reports.  Product runtime loaders and generated evidence
remain outside behavioural scope except where a shared safe loader is already
their public dependency.

## Questions the design must answer

1. Which tools may use `chrona.resources.safe_load`, and which must retain an
   independent loader because their tests deliberately prohibit a `chrona.`
   import?
2. How can a run-local path cache preserve fresh reads, deterministic error
   reporting, and test isolation without adding cross-run cache state?
3. How is the semantic-reachability AST traversal made exactly once per check?
4. How can realization coverage discover its slides once per render while
   retaining its current output bytes and independent renderer boundary?
5. Which structural and characterization tests prove that speedups do not
   conceal a stale resource, change YAML semantics, or relax coverage?

## Required outputs and release gate

The English design must define loader ownership, cache lifetime and keys,
error behaviour, and a source-level no-direct-`safe_load` policy.  Its
architecture review must verify that tools remain deterministic evidence
generators, presentation coverage remains independent of product imports, and
no production or CI test is omitted.  The implementation plan must split
reachability, loader/caching, and evidence verification into reviewable units,
then benchmark the focused paths and publish normal CI evidence.

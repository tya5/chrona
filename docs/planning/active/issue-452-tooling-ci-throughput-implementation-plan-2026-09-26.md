# Implementation Plan — Tooling CI Throughput (#452)

**Design:** `83c4f41a`.
**Architecture review:** `39c2725b`.

## I452-1 — Reachability traversal closure

Hoist `reachable_semantic_ids(root)` out of the per-identifier generator in
`missing_semantic_ids`.  Add a focused test that spies on the traversal and
proves one call preserves the existing missing-id result.

**Acceptance:** the reachability command and its unit suite pass; the source
contains one production AST traversal per command invocation.

## I452-2 — Safe loader and run-local coverage reuse

Introduce an independent CSafeLoader-backed run-local loader in presentation
coverage.  Thread it through discovery and live-schema loading.  Change
semantic-realization coverage to discover slides once.  Route all remaining
direct YAML safe-load call sites in `tools/` and `src/` through the canonical
safe loader where that does not violate an independent-tool boundary.  Add
structural and freshness tests.

**Acceptance:** repeated reports retain byte identity; malformed input retains
its documented diagnostic; rewritten files are observed by a new run; the
presentation coverage source has no `chrona.` import and all production/tools
direct `yaml.safe_load` calls are gone.

## I452-3 — Evidence and release gate

Run focused tool tests, report `--check` commands, materializer characterization
and duration samples.  Review generated differences, run the structural
policy, publish the implementation, and use CI for the full parallel suite.

**Acceptance:** no focused regression; each report is current; CI is started
from the published commit and its full test/check status is recorded before
#452 is closed.

# Implementation Plan — Reproducible Example Evidence and Reachability (#441)

**Design:** `issue-441-reproducible-example-evidence-design-2026-09-26.md`.
**Architecture review:**
`issue-441-reproducible-example-evidence-architecture-review-2026-09-26.md`.

## I441-1 — Typed reachability and README evidence gate

Implement a deterministic tracked-file graph rooted at corpus manifests. Follow
only typed local manifest/Context/snapshot/icon-resource edges; report missing,
escaping, duplicate, and unreachable files. Expose the reachable View paths
for schema tests. Add root README image discovery and require any `examples/`
image target to equal one declared `expectedSvg`. Integrate the checked
reachability command into conformance.

**Files:** new repository-quality tool and focused tests; manifest/context
parsing helpers; `check_documented_commands.py` or its sibling; View schema
test population; conformance registry.

**Acceptance:** an orphan fixture fails; a missing typed local resource fails;
the ASTER old preview path fails README validation; the declared generated
ASTER SVG passes; current reachable Views validate without a skip path.

## I441-2 — Atomic ASTER cleanup and evidence migration

Delete the legacy ASTER slides tree, gallery HTML, and Views 02–05. Update the
root README hero/caption and ASTER README to describe the one manifest-owned
generated SVG. Regenerate only derived inventories/reports affected by tracked
corpus population. Do not preserve a compatibility symlink or copied PNG.

**Files:** `README.md`, ASTER README/example topology, obsolete paths,
generated inventories, release review.

**Acceptance:** none of #441's listed paths exists; all tracked example files
are reachable or explicitly reasoned; README image target is declared
materializer evidence; public materializer reproduces every corpus slide.

**Publication dependency:** I441-1's strict enforcement and I441-2's ASTER
deletions publish in one atomic commit. A standalone enforcement commit would
intentionally fail against the known legacy population it is meant to remove.
Focused checker development remains independently testable before that release.

## Verification and publication

Run focused reachability/readme/schema tests per slice, then all public
materializer reproduction once for the final artifact topology. Run
generated-document and conformance checks, inspect generated SVG differences,
and run `git diff --check`. Use one remote CI observation only after the final
published material change; do not duplicate full local pytest.

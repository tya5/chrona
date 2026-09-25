# Implementation Plan — Visible Fit and Placement Failure Policy (#449)

**Design:** `cdbde2fc`.
**Architecture review:**
`issue-449-visible-fit-failure-architecture-review-2026-09-25.md`.
**Supersedes:** the implementation portions of the #400 row-density plan that
preserve fit/placement refusal.

## Preconditions

- Do not publish the uncommitted I400-1 v0.9 `diagnose` contract.
- Each source slice begins by fetching `origin/main`, checking its exact base,
  and publishing serially.
- A discovered fallback that cannot be represented by completed Layout geometry
  returns to design review; no use-case, Scene, or renderer workaround is
  permitted.

## I449-1 — Common contract and clean resource migration

Amend ADR-0031 and Specifications 08/50.  Introduce typed `FitWarning` and
completed canvas bounds at the Layout → Scene contract, including versioned
Scene serialization/schema support.  Replace all live `diagnose` fit/placement
declarations with `visible-overflow` in a single v0.8 → v0.9 Profile/View and
Context migration; delete the v0.8 reader and do not retain a compatibility
normalizer.  Retire the unpublishable I400-1 row-density type/policy changes.

**Acceptance:** no live resource has `diagnose`; all affected schemas and
inventory entries agree; warning/canvas values cannot be incomplete; existing
ordinary outputs have unchanged geometry and an explicitly reviewed identity
only Scene diff; schema, closure, vocabulary and public materializer checks
pass.

## I449-2 — Completed canvas transport

Make Layout return a deterministic canvas containing all completed placements.
Thread it unchanged through Scene, inspection serialization, `render_review`,
SVG, PNG, PDF, Typst and TikZ.  Remove fit-specific render preflight refusal.
Add target contract tests proving that no serializer selects canvas extent or
uses a crop as a fallback.

**Acceptance:** a neutral overflowing placement expands the emitted artifact
for every target; Scene and CLI receive the same typed warning; a fixed draft
and immutable Context both produce an artifact; structural tests forbid a
fit/placement `RenderFailed` path.

## I449-3 — Slot, table, row, and mark visible fallbacks (#400 core)

Replace required-slot/table errors with natural-size visible placements where
`visible-overflow` is selected.  Make row requirements, tracks and marks retain
their P1 geometry and extend the completed surface/canvas rather than compact,
clip, or reject.  Keep author-selected ellipsis/wrapping/clipping behavior
unchanged and explicit.  Emit one typed warning per completed affected
placement.

**Acceptance:** dense multi-lane/multi-milestone rows, oversized table text,
and overflowing marks all render with retained identities and inspectable
warnings; no global mark-containment weakening occurs; old explicit degradation
fixtures remain deterministic.

## I449-4 — Label, axis, route, group, and network fallbacks

Replace label refusal with the deterministic preferred overlap placement;
restore all axis labels on the normal path; use a direct deterministic relation
path when quality routing fails; stack group headers/milestones; and extend
network bounds.  Keep suppression and thinning only when declared by the View.
Remove all remaining user-reachable fit/placement refusal paths in the
source-derived registry.

**Acceptance:** each registry family has a neutral fixture with an artifact,
warning and completed Scene evidence; explicit suppression/thinning fixtures
still carry their declared records; the registry structural test has no
unclassified reachable fit/placement error.

## I449-5 — Corpus, public evidence, and release gate

Regenerate affected profiles, Context closures and all public materializers in
one batch.  Review generated SVG and PNG changes, including expanded canvases
and intentional overlaps.  Run focused tests after each prior slice, then full
pytest, conformance, every public materializer, schema/vocabulary/diagnostic
inventories, coverage and structural gates, wheel smoke, and three-platform
CI.  Publish an English acceptance review, then close #400 and #449 only when
the source registry and evidence are both complete.

No slice may make `suppress` implicit, hide a warning from Scene or CLI, retain
the old `diagnose` reader, or rely on target-specific clipping for a visible
fallback.

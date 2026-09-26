# Implementation Plan — Publish Approved Visual Targets (#462)

**Design base:** `2e9019460a77ec585b3a1638e9f83b550331ddb8`.
**Authorities:** [design](../../design/issue-462-design-target-publication-design-2026-09-26.md),
[architecture review](../../reviews/current/issue-462-design-target-publication-architecture-review-2026-09-26.md),
[issue #462](https://github.com/tya5/chrona/issues/462).

## Literal acceptance gates

1. PR #461 is merged.
2. Target B's generator and rendered images are on `main` outside `examples/`.
3. #453 links to target B on `main`.

## I462-1 — Fourteen targets

Re-read PR #461's exact head, file list, checks and mergeability against the
fresh remote `main`. Merge the PR without force or unrelated changes. Verify
its merged state and that all fourteen named directories each contain the
README, HTML source and PNG on `main`. The merge commit is the first
publication boundary. Any conflict or unexpected remote change stops this
slice for reconciliation.

## I462-2 — HALCYON-1 target B

From the published `design/halcyon-1-target` branch, copy only
`docs/research/presentation/halcyon-1-target-design-2026-09-21/render_mocks.py`
and its README plus nine PNG/SVG pairs from `examples/halcyon-1/slides/`.
Place the pairs under the research directory by proposal. Update that README
with new generation/raster instructions and target B link. Do not add
anything under `examples/` or change product code. Check copied file bytes
against the branch's Git blobs, inspect all nine images/headers and the B
render, run research-source and example-reachability/conformance checks.
Publish this as the second coherent commit after fetching/checking `main`.

## I462-3 — Live link and acceptance

Only after the B commit is remotely visible, edit #453's issue body to point
to the `main` B PNG and verify the fetched body. Then write a literal-
acceptance review in `docs/reviews/current/` with PR #461 merge SHA, B SHA,
branch-byte audit, #453 link and CI/reachability evidence. Publish review as
a third coherent commit; inspect its CI release gate. Close #462 only after
all three literal rows are met. Leave #453 open as its owner-maintained gap
map. There are no schema migrations, public materializers or generated corpus
outputs in this issue.

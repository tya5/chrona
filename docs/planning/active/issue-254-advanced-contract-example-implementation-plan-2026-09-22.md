# Issue 254 Advanced-Contract Example Implementation Plan

**Design authority:**
`docs/reviews/current/issue-254-advanced-contract-example-design-2026-09-22.md`

## Preconditions

Implement only the released Project v0.5 and View v0.8 paths described by the
design. No schema, closure, scheduler, Layout, Scene, renderer, or target
capability change is authorized. If the example cannot express a required
assertion through those paths, stop and publish a design correction.

## Atomic implementation slice

**E254-1 — Flight-readiness closure and public evidence.** In one PR:

1. Extend HALCYON's Project with the declared rollup tree, unique WBS labels,
   planned-progress values, and one PSR link. Add the hierarchy/scenario/
   critical View, its complete SVG Render Context, and its manifest entry.
2. Regenerate only `generated/06-flight-readiness.svg` using the public
   materializer. Check that the five pre-existing generated SVG hashes are
   unchanged before committing the new artifact.
3. Make integration/acceptance discovery enumerate every HALCYON manifest
   slide rather than maintaining a stale hand-written subset. Add a focused
   public-artifact assertion for hierarchy rows, WBS and total-float cells,
   selected Scenario provenance, the PSR title anchor, and critical dependency
   roles.

**Acceptance:** Project validates and schedules; the sixth context resolves a
complete closure; all manifest slides reproduce byte-for-byte through the
public materializer; focused semantic assertions pass; generated-output and
closure-read gates cover the sixth slide; and the full pytest suite passes.

## Release review slice

**E254-2 — Acceptance and architecture review.** After E254-1 is merged,
record the exact focused/full test commands, verify the pre-existing artifact
hashes and the new artifact's source/role/link semantics, and re-check that no
implementation crossed the Project → View → Layout → Scene → renderer
boundary. Publish this review and then close #254.

## Publication discipline

Each slice is a separate PR. Before each merge fetch `origin/main`, inspect
the exact range and mergeability, require all CI checks, merge serially with a
non-force squash merge, then verify the merged commit on GitHub and use the
merged commit as the next base.

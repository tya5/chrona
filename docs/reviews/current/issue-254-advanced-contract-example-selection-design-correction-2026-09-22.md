# Issue 254 Advanced-Contract Example Selection Design Correction

**Corrects:**
`docs/reviews/current/issue-254-advanced-contract-example-design-correction-2026-09-22.md`

## Trigger and decision

The public materializer gate proved that `halcyon-02-programme-board` uses a
type-only automatic selector. A newly authored rollup is a scheduled span and
therefore becomes eligible for that View, changing its generated SVG. View
v0.8 has no exclusion selector, so preserving the five established artifacts
requires the existing programme-board View to declare its current selected
object IDs explicitly.

E254-1 will replace the type-only selector in `02-programme-board.yaml` with
the exact IDs already represented by its current generated artifact, retaining
the existing `[span, point]` type guard, ordering, grouping, and all other
View policy. The new `mission-closeout` root is intentionally absent. This is
a View-owned selection correction, not a Project scheduling or Layout policy.

## Acceptance

The program-board SVG byte hash must equal its pre-#254 hash. The other four
pre-existing HALCYON hashes must also match, while the sixth artifact is the
only added generated SVG. The public-materializer test enumerates the manifest
instead of a hand-maintained subset.

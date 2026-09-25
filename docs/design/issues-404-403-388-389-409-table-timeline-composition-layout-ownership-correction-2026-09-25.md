# Design Correction — Row Allocation Ownership (#404, #388)

**Status:** Accepted correction to the P1 design before I2 implementation.

## Finding

The approved design correctly assigns row surplus distribution to Layout
Profile, but the live `layout-profile/v0.4` has no review-surface policy
subtree. Conversely, all physical measurement metrics consumed by Layout are
already resolved through Theme metrics. Adding `pack|fill` as an implicit
default or as a Theme token would make a structural arrangement decision
invisible or style-owned.

## Corrected ownership

P1 introduces `layout-profile/v0.5` with a finite, surface-scoped policy:

```yaml
reviewSurface:
  rowDistribution: pack # pack | fill
```

The field is required for every v0.5 profile. It applies only to the
table--timeline review surface; it is neither a generic container
`justifyContent` alias nor a renderer option. `pack` retains each completed
row's required extent and leaves surplus after the final row. `fill`
distributes only remaining block space deterministically after all required
extents and group-header extents have been reserved.

P1 also introduces `theme/v0.10` with `timeline.row.paddingBlock` in the
existing Theme metric vocabulary. This is a measured physical distance used
while deriving each required row extent, beside `timeline.row.minBlockSize`
and `timeline.mark.blockSize`. It cannot select `pack` or `fill`.

## Failure and placement boundary

Layout computes each row's requirement from completed track feasibility, the
Theme row minimum, and `timeline.row.paddingBlock`; it then applies the
Profile distribution. If the sum cannot fit, it delegates only to the
visible-failure policy from #400. Scene receives already assigned row bounds
and never performs distribution, padding, or overflow interpretation.

This correction does not alter I3 ownership: View still selects decorations,
Theme resolves their treatment, and Layout computes their completed bounds.

## Migration

The P1 release migrates every live Layout Profile to v0.5 and every live Theme
to v0.10, with no v0.4/v0.9 runtime ingress. The v0.10 schema admits the P1
background-role vocabulary required by I3 so that one coherent Theme contract,
rather than a temporary compatibility version, governs I2 through I4.

# Architecture Review — Background Extent Correction (#389, #409)

**Decision:** Accepted.

| Boundary | Review result |
| --- | --- |
| View / Layout Profile | Pass. The View selects finite row/group membership; the Layout Profile selects finite slot reach. Neither is overloaded with the other's responsibility. |
| Theme / Layout | Pass. Treatment, opacity and ordering remain Theme inputs; physical union and overlap validation remain Layout work. |
| Layout / Scene | Pass. Layout completes every rectangle and uses a truthful slot or review-container identity. Scene cannot widen, split or reorder it. |
| Specification 50 | Pass. The overlap rule is a completed-placement invariant over actual bounds and alpha, not a renderer convention. |
| Specification 55 | Pass. `backgroundExtents` is a small review-surface arrangement policy alongside `rowDistribution`; it is not a Theme style token or reusable generic layout language. |
| Specification 63 | Pass. The finite role mapping preserves typed, renderer-neutral Scene output and does not introduce generic layering. |
| Migration | Pass. A v0.6 atomic migration avoids an ambiguous v0.5 default and preserves the project's no-compatibility policy. |

## Required implementation checks

1. Reject a v0.6 profile missing, duplicating or extending the four finite
   extent members.
2. Test `table`, `timeline` and `both` bounds and the corresponding placement
   identity.
3. Test that `alternate-rows` cannot emit group body fills, and that a
   translucent fill overlap fails before Scene.
4. Verify Scene projects the resolved bounds/identity/order without geometry
   reconstruction.
5. Regenerate every public materializer output after the atomic schema and
   resource migration.

The correction resolves the #389/#409 conflict structurally.  It may proceed
to implementation planning.

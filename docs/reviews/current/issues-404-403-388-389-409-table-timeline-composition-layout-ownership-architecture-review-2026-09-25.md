# Architecture Review — Row Allocation Ownership (#404, #388)

**Decision:** Accepted. The correction is required before I2 implementation.

| Boundary | Review result |
| --- | --- |
| Layout Profile / Theme | Pass. Profile owns the finite structural `pack|fill` policy; Theme owns only measured physical row padding. |
| Layout / Scene | Pass. Layout completes row bounds and failure classification before projection. |
| Surface specificity | Pass. `reviewSurface.rowDistribution` cannot accidentally change generic container free-space distribution or dependency-network layout. |
| Migration | Pass. v0.5/v0.10 successors avoid a partial compatibility reader and give I2--I4 one contract base. |

The alternative of retaining uniform division until a later profile change
would preserve the exact accidental authority #388 identifies. The
alternative of a Theme `pack|fill` token would let visual style change
structural geometry. Neither is acceptable.

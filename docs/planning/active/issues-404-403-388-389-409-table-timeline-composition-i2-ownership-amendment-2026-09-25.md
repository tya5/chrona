# Implementation Plan Amendment — I2 Row Allocation Ownership (#404, #388)

**Applies to:** I2--I4 of the published Table--Timeline Composition plan.

Before changing `place_rows` or measured table allocation, I2 must create and
migrate `layout-profile/v0.5` and `theme/v0.10` as specified by the accepted
ownership correction. It must then:

1. require `reviewSurface.rowDistribution` and `timeline.row.paddingBlock`;
2. derive a per-row required extent by invoking the existing track feasibility
   path, then adding padding and enforcing the Theme minimum;
3. reserve group-header extents before applying deterministic `pack|fill`;
4. delegate an infeasible sum to the #400 visible-failure policy rather than
   retain the uniform-row overflow path; and
5. prove that Profile policy and Theme measurement cannot be read by Scene or
   an adapter.

The v0.10 schema and corpus migration also include the finite P1 background
role vocabulary required by I3, but I2 must not emit decorations or introduce
background ordering before I3's placement/invariant work is complete.

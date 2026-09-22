# Issues 274–277 Collision-Domain Correction

## Trigger

Replacing the old same-region filter with an unconditional all-text comparison exposed
that `collision_region` was carrying two incompatible meanings: diagnostic provenance
and an implicit physical lane. Axis coarse and fine labels, for example, are separate
stacked lanes but their measured boxes can meet at a baseline boundary. A global pairwise
rule therefore rejects valid two-level axes instead of detecting overlays.

## Corrected model

Layout must construct an explicit typed **collision domain** for every text placement.
A domain represents one physical plane in which text cannot overlap: table cells in the
same row band, one axis label lane, one overlay plane, a plot-label plane, and so on.
The existing region remains explanatory provenance only. Domains are assigned by the
Layout composition that owns the relevant slot/overlay relationship, never by Scene or
renderer code.

`SurfacePlacement.assert_valid` compares all required non-suppressed text placements
whose collision domains intersect. Normal row/column/axis lanes are structurally
disjoint domains; overlay children deliberately inherit the parent plane and therefore
are checked against underlying text. This preserves #274's requirement: cross-region
overlay text cannot escape validation merely because its provenance differs.

## Consequence

The rejected PR #294 must be amended rather than merged. Tests require both a
cross-region same-domain rejection and a coarse/fine axis different-domain acceptance.
The planned #277 axis work may refine domains but cannot use collision-region strings as
an exemption mechanism.

# Architecture Review — I2 Label-Obstacle Correction

**Decision:** Accept.

The correction preserves the architecture boundary. Layout owns completed
marks, labels, collision candidates, and row extents; Scene remains a pure
projection of those placements. Profile still owns only surplus distribution,
Theme only physical measurements, and View only declared label policy.

Rejecting all non-host mark intersections is preferable to increasing every
row for arbitrary label text: the latter would mix overlay policy into track
feasibility, duplicate the label solver, and make `pack` content-dependent in
an unbounded way. Context-aware failure wording remains in `render_review`,
not in the geometry primitive.

Required evidence: direct host/non-host obstacle unit coverage, public SVG
property checks, draft and immutable overflow checks, and the complete suite.

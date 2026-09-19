# Gantt reference correction — analysis and design gate

Reference: user-supplied 1789834591827.png, compared directly against ff33e6f SVG.
Scope: Gantt only. M23 observation tables and milestone digests remain deferred.

## Findings

- Table consumes ~40% versus reference ~28%; surplus columns weaken hierarchy.
- Owner text overruns; text/bar baselines sit near group bottoms, not row centers.
- Month and quarter labels spill into the table, grids extend below the chart.
- Canvas width is incorrectly reduced by its margin (1528 instead of 1600).
- Point connector anchors stay at timeline origin; endpoint types are ignored.
- Group colors depend on prior row counts; density silently enables merged owners.
- Weak font/bar hierarchy; variance is distant from the associated bar.

## Closed correction contract

The existing Layout Profile gains optional closed `surface` settings (schema is
normative): group mode/label/fraction/gap, month/quarter levels, typography sizes,
bar dimensions and variance visibility. Defaults apply to absent settings; density
must not select grouping semantics. Geometry remains derived from solved rectangles.
View gains optional `grouping.order`; unlisted groups follow in stable ID order.
Within-group ordering remains View-owned. Theme roles `group:<group-id>` bind color
to stable group identity, falling back to `group-band`, never to preceding row count.
These are generic identifiers, not branches on sample IDs or titles.

Explicit View windows must be honored; selected-comparison includes observed dates.
Month bands are clipped to the window, centered in their visible intervals. All rows
share table/timeline centers. Group labels wrap within their own column; row rules
do not cross merged cells. Font families remain Theme-owned. Conservative wrapping
is not a guarantee for arbitrary font metrics; required text overflow must diagnose.

Relations use each declared start/end/at endpoint. Orthogonal routes use obstacle
edges and row gutters, avoid bar/label interiors, and diagnose if no route exists.
Routing never changes dates or relation direction. Arrowheads terminate at shapes,
not at the table boundary. Missing Actual and unmatched inputs remain explicit.

Legend uses the existing legend slot and fixed semantic roles; supplier commentary
and extra dashboards are excluded. No Project/Actual data changes are authorized.

## Acceptance

Schema validation, geometry/endpoint regression tests, alternate layout settings,
unchanged Project/Actual inputs, byte determinism, full suite, and raster comparison.
Passing earlier tests alone is not evidence of visual correctness. Publish this gate
before implementation; publish completed correction after visual review.

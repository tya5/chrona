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

## Implementation and visual review

Design gate published as `d4565d5` before implementation. The prior table renderer
was replaced by a single generic `gantt_surface` adapter, not a sample-specific path.
The executive preset now supplies a dedicated View, a 3:7 split, merged groups,
explicit February-to-July-1 window, month-only calendar, 19px body / 24px group /
40px title typography, and 17px paired bars. Project and Actual resources are unchanged.

Visual loop: inspected reference + old raster, inspected new raster, corrected the
exclusive end-month caption, rerendered and checked the final artifact. Typography
uses installed Nimbus Sans with Arial/sans-serif fallbacks. The Sharp-based verifier
measures all 15 wrapped table/group text lines with the rasterizer: zero horizontal
overflows. Final output is truly 1600x900. The legend explains semantics and reports
missing/unmatched data; no supplier panel or milestone digest was implemented.

Regression evidence: 12 new tests cover endpoint anchors, start-to-start dependency,
orthogonal obstacle avoidance (including every sample bar), grid bounds, group-color
stability, explicit windows, Actual-inclusive automatic windows, resource validation,
overflow diagnosis, alternate group mode, relation visibility, and determinism/input
immutability. Full suite: 104 tests. Full existing conformance: PASS.

Remaining limits: this is a reference-inspired layout, not pixel identity. The
underlying plan has different tasks, dates and Actual coverage. Grouping may require
upward dependency arrows. Fonts are not embedded; other machines may use fallbacks.
Conservative runtime wrapping is supplemented by raster verification for this preset,
not a claim of universal font/layout correctness. Route-vs-route crossings are not
globally optimized; routes avoid bar interiors. M23 external panels remain deferred.

Reproduction (repository root):

```sh
PYTHONPATH=src .venv/bin/chrona render-review examples/controller-z-silicon-bringup.yaml --actual examples/controller-z-actual.yaml --view examples/controller-z-executive-view.yaml --style examples/controller-z-review-style.yaml --theme examples/controller-z-executive-theme.yaml --profile examples/controller-z-executive-layout.yaml --output examples/controller-z-executive.svg
NODE_PATH="$CODEX_PRIMARY_RUNTIME_NODE_MODULES" "$CODEX_PRIMARY_RUNTIME_NODE" scripts/verify-gantt-svg.cjs examples/controller-z-executive.svg examples/controller-z-executive.png
```

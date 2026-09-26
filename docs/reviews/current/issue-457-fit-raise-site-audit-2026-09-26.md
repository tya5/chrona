# Fit Raise-Site Audit — Issue #457

**Code base:** L2 implementation after `71593626`; release acceptance remains
subject to the final CI run and [implementation plan](../../planning/active/issues-457-447-fit-and-host-font-implementation-plan-2026-09-26.md).

This is a source-site audit, not a claim that an old green run proves current
behavior. `E_LAYOUT_REQUIRED_OVERFLOW` has **zero** remaining raises in
`presentation/layout`. The table records each remaining fit-named raise and
its path disposition. “Invalid” means the input violates a non-fit contract;
“caught” means the candidate failure is deliberately converted to a
completed fallback; “invariant” means a post-measurement internal contract
check, not a branch for ordinary viewport shortage.

| Source site | Disposition | Evidence / required guard |
| --- | --- | --- |
| `annotations.route_annotation_leader`: invalid `limit` | Invalid | A positive caller-owned search limit is required. |
| `annotations.route_annotation_leader`: search budget exhausted | Caught | Surface composition emits a direct leader with `W_LAYOUT_ROUTE_FALLBACK`. |
| `annotations.route_annotation_leader`: no route | Caught | Same direct-leader fallback. |
| `routing.route_orthogonal`: search budget exhausted | Caught | Both Gantt and network relation composition emit direct-path warnings. |
| `routing.route_orthogonal`: no obstacle-free path | Caught | Both callers use the same direct-path fallback. |
| `axis.thinning_schedule`: no fitting subset | Caught | Axis composition retains all intervals as visible overflow. |
| `presentation.MarkGeometry.__post_init__` | Invalid | Theme role fraction/offset cannot describe a contained mark. |
| `presentation.place_table_columns`: negative gutter | Invalid | Resolved metric is not a nonnegative distance. |
| `presentation.place_table_columns`: multiple fill maxima | Invalid | Mutually conflicting column policy, independent of viewport. |
| `presentation.place_mark_tracks.require_contained` | Caught/invariant | Row-minimum search catches candidate failures; final caller supplies that measured minimum. |
| `presentation.place_mark_tracks`: row below stacked minimum | Caught/invariant | Same row-minimum search and final measured requirement. |
| `presentation.minimum_track_block_extent`: nonpositive mark size | Invalid | Resolved Theme/metric cannot give a positive mark extent. |
| `dependency_network.place_dependency_network`: nonpositive node minimum/negative gap | Invalid | Resolved metric contract, not available viewport size. |
| `dependency_network._assert_surface_quality`: coincident ports | Invariant | Exact completed node geometry must have distinct ports. |
| `dependency_network._assert_surface_quality`: node overlap | Invariant | Rank/row placement uses measured node sizes and gap before this check. |
| `dependency_network._assert_surface_quality`: text outside node | Invariant | Node size is closed from its text measurement before placement. |
| `labels._candidate`: too-large `inside` candidate | Caught | Candidate search skips it; visible fallback uses natural position. |
| `labels.place_label`: no legal visible candidate | Invalid | Requires an empty/unknown candidate vocabulary after validated View ingress. |
| `labels.place_label`: required nonvisible policy exhausted | Invalid/explicit | Required `clip-optional` is invalid; explicit suppress is a selected omission. |
| `surface_composer`: malformed placed axis outcome | Invariant | Thinning-impossible branch now marks a nonfitting retained interval as visible overflow. |
| `surface_composer`: no plot-label candidate or suppress rung | Invalid | Normalized View must declare a placement/suppression choice. |
| `surface_composer`: visible annotation fallback returns no box | Invariant | `visible-overflow` placement is total for validated candidate sides. |
| `profile.visit`: dual aspect-ratio sizes | Invalid | Two dependent dimensions cannot determine one node. |
| `profile.visit`: center-to-center anchor with gap | Invalid | Contradictory authored anchor constraint. |
| `profile.visit`: grid aspect-ratio track | Invalid | Unsupported structural track shape. |
| `profile.visit`: grid child outside declared tracks | Invalid | Invalid cell reference. |
| `engine.solve_layout`: nonpositive viewport | Invalid | Viewport must have positive finite extents. |

Other checks such as missing measurement, missing visual target, invalid
icon/Theme ratio, and duplicate placement identity are input/closure checks,
not fit refusal. The L2 tests exercise negative canvas origin, text-plus-icon
natural fallback, and immutable narrow rendering. The release review must
recheck this inventory after CI and the public byte comparison; discovery of
any valid-fit escape reopens design before issue closure.

The render use case no longer contains the historical immutable
`E_LAYOUT_REQUIRED_OVERFLOW` rematerialization rewrite; a structural test
guards both that and the absence of a production Layout raise site.

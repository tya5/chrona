# #1373 row 3: implementation plan

Authority: [design](../../design/issue-1373-hosted-points-design-2026-10-15.md),
[architecture review](../reviews/issue-1373-hosted-points-architecture-review-2026-10-15.md),
and [Spec 50 section 3.5](../../specification/50-constraint-driven-gantt-surface-quality.md#35-physical-point-hosting-1373).
Design published as `c157522e5`; input slice published as `563685c8e` after
#1397 row 3 merged in PR #1523. Adopt current trusted main before the final push.

## One feature PR, independently checked commits

| Slice | Owners/files | Acceptance and focused checks |
| --- | --- | --- |
| 1. Closed inputs | `model/projection.py`, `schemas/layout-profile-v0.10.schema.yaml`, `layout/model.py`, `layout/engine.py`; pure Layout host-resolution records/helper | Preserve original `attachesTo` separately from derived `attached_to`, including Snapshot/Scenario parent/source facts. Default-off profile normalization and canonical bytes; malformed schema rejection; source/facet/interval/selection/occurrence precedence tests. |
| 2. Shared physical allocation | `layout/lane_item_footprints.py`, `lane_subtracks.py`, `surface_lanes.py`, `lane_label_preflight.py`, `surface_marks.py`, `mark_geometry.py` and typed placement records | Resolve once from source facets and visibility. Derive physical-only allocation inventory; exact source-facet partition, explicit hosted-only units, exact overlap pairs, host-relative frames, original semantic tracks and final-footprint equivalence. Planned/Actual may have different physical hosts. Fixed glyph conflict has a named error, not date movement or suppression. |
| 3. Completed downstream consumers | `surface_member_labels.py`, `ports.py`, `surface_routes.py`, `surface_annotations.py`, final completion/validation owners | Physical-row label demand/candidates with unchanged semantic identity; all endpoint, hint/recovery and annotation paths retain exact-host corridor authority. No host-wide route exemption. Parts, bound icons, ports, window originals/visible records and lane emissions match final geometry. Scene/adapters do not place or infer hosts. |
| 4. Acceptance/publication | Synthetic unit/integration fixtures, gap report, concise issue acceptance review | Actual SVG and typeset evidence; default-off public-materializer batch diff; schema equivalence; focused regressions; current-head PR gates and exact review-containing main three-OS release. Keep parent issue open until every literal row is met. |

Before shared-file writes, inspect dev B's current claim/PR and coordinate any
overlap. Do not edit `examples/**` or bot-owned generated reports. No packaged
Theme adaptation is required; authors opt in and tune existing Theme roles.

Route API correction: keep legacy comparison `host_ids` separate from new
physical `corridor_host_ids`. Validate physical authority only inside recorded
endpoint corridors, splitting a reduced segment at exposed boundaries; preserve
physical host obstacles in recovery. Cover reduction, terminal setback, re-entry,
fanout, hint and annotation paths before connecting physical neighbour discovery.
This corrects the consumer contract, not the selected hosting behavior.

## Required synthetic evidence

- Each declared link; eligible attachment precedence; parent fallback; direct
  parent only; absent/outside/unselected/nondrawable host leaves the point unchanged.
- Inclusive start/end dates, separate half-open window admission; clipped host,
  omitted point, hidden rollup and folded header; source/facet/scenario isolation.
- Multiple occurrences (same-row unique, source unique, explicit ambiguity error),
  cross-row parent with labels and dependency/annotation endpoints enabled.
- Default-off identity; exact point date and Theme size; transformed glyph parts,
  mark-bound icon, ports/provenance, paint order and actual-ground contrast.
- Preflight/final physical-frame equality, each semantic facet exactly once,
  hosted-only child accounting and unchanged lane/table membership. Verify
  non-hosted Actual geometry when only the planned point is hosted, and vice versa.
- Exact host-only egress; an unrelated obstacle still blocks the corridor and
  the host still blocks route-body re-entry; no silent relation loss.
  Also test the span's start/end dependency with an inclusive endpoint milestone:
  reciprocal authority covers only that covering point, not other hosted points.
- Two hosted points with incompatible fixed footprints produce
  `E_LAYOUT_POINT_HOST_OVERLAP`; no hidden glyph or new subtrack fallback.

Use existing unit homes for `test_projection_rows`, `test_lane_subtracks`,
`test_lane_window_marks`, `test_ports` and integration attached milestones;
add one synthetic hosted-point integration fixture rather than a corpus sweep.
Run local focused tests in this worktree's venv, schema equivalence against
current main and documentation/literal-review checks. CI supplies full pytest,
conformance, newest-Python materializers and three-OS release; do not duplicate
the full local suite. Inspect all changed public SVG/Scene/report bytes together.

The final acceptance review copies all four literal issue rows (1, 2, 3, 6),
joins prior merged row evidence to this exact release, and explicitly separates
developer capability from reviewer-owned design adoption. Archive only after
actual closure; do not claim completion from this plan.

Current implementation: allocation/geometry `267c95fb2`, corridors `0f4ad4945`.
The [acceptance review](../reviews/issue-1373-editorial-capabilities-acceptance-review-2026-10-15.md)
tracks all literal rows and remaining release evidence. Focused tests include
SVG/typeset rendering, deliberate final-frame drift, non-lane conflicts and
reciprocal egress; no examples or generated reports were edited. Final-head
artifact inspection and exact-main three-OS release are still required.

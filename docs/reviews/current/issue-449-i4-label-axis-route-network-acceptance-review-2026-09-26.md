# Acceptance Review — Visible Label, Axis, Route, Group, and Network Fallbacks (#449 I449-4)

**Design:** `issue-449-visible-fit-failure-policy-design-2026-09-25.md`.
**Implementation plan:** `issue-449-visible-fit-failure-implementation-plan-2026-09-25.md`.

## Decision

Accepted.  I449-4 completes the remaining fit/placement families in Layout.
Normal labels retain their first declared candidate when no collision-free
candidate exists.  Axis labels retain every declared interval unless the
author-selected `thin-with-record` policy can produce its explicit result;
an impossible thinning selection falls back visibly.  Quality routing falls
back to the direct endpoint path, folded header marks extend their real group
header host, and dependency networks retain natural measured geometry in an
expanded completed canvas.

## Boundary review

All fallbacks and `FitWarning` records are selected before Scene projection.
Scene carries only completed placements, canvas bounds, and warning values;
adapters do not choose routes, labels, or extents.  Invalid graph topology,
unknown references, invalid metrics, and resource failures remain errors.

## Evidence

| Family | Completed behaviour | Warning |
| --- | --- | --- |
| Plot and relation labels | First declared candidate, including overlap/escape | `W_LAYOUT_LABEL_OVERFLOW` |
| Axis labels | Every label; explicit thinning only when it succeeds | `W_LAYOUT_LABEL_OVERFLOW` plus existing declared thinning records |
| Relations | Direct endpoints when quality routing cannot complete | `W_LAYOUT_ROUTE_FALLBACK` |
| Folded group headers | Stable stacked marks in an expanded `GroupPlacement` header | `W_LAYOUT_GROUP_HEADER_OVERFLOW` |
| Dependency network | Natural node/title extent and direct edge fallback in completed Layout canvas | `W_LAYOUT_NETWORK_OVERFLOW`, `W_LAYOUT_VISIBLE_OVERFLOW`, or `W_LAYOUT_ROUTE_FALLBACK` as applicable |

## Generated evidence review

Controller Z `executive`, `elevated`, and `composition-compact` regenerate
only relation-label provenance: each label now carries the relation that owns
it, rather than the last relation traversed by the former loop.  Their visible
geometry is unchanged.  This updates both SVG `data-source-ref` and Scene
`sourceRef` and introduces no unneeded fit warning.

## Verification

- Focused label, network, Scene, and render tests: 70 passed.
- Public materializer suite: 25 passed after regenerated evidence.
- Diagnostic inventory freshness, Scene primitive-delivery structural check,
  and conformance: passed.

I449-5 remains the release batch: corpus-wide generated-artifact review, full
test suite, all target checks, and three-platform CI before #400 and #449 can
close.

# Issue #1114: endpoint-mark routing

Predecessor: [design plan](../planning/active/issue-1114-endpoint-mark-routing-design-plan-2026-10-04.md).
Normative authority: Specification 50 §3.3, coordinated with Specification 33
§8's comparison-host corridor contract.

## Contract

Layout rejects traversal of an endpoint's primary mark, as it already rejects
foreign primary marks. A span start offers start/above/below exits, never its
far end; finish/end mirrors this. Above/below corridors retain the temporal
endpoint coordinate. Point/body ports remain boundary ports, not centre ports.
Remaining candidate order stays unchanged; there is no project-specific rule.

The completed path must clear primary mark interiors (bounds inset by half
the relation stroke width, allowing boundary ink contact). Test every segment,
including diagonal visible-overflow segments. Apply the same predicate after
repair, in lane and non-lane selection, to the back-route, and before emitting
visible overflow. Named comparison-host corridors keep Spec 33's narrowly
scoped exemption; no exemption applies to a primary mark's interior.
Rounded paths must also clear these interiors; centred-terminal trimming cannot
introduce a crossing. Scene observes completed geometry but never repairs it.

If no safe route fits, existing explicit suppression applies. Visible overflow
may relax the usual feasibility bounds, but may not waive primary-mark safety;
an unsafe direct fallback is suppressed with `W_LAYOUT_RELATION_SUPPRESSED`
and `I_LAYOUT_RELATION_MARK_BLOCKED:<relation id>`. Lane candidate failures retain
typed `E_LAYOUT_ROUTE_THROUGH_MARK` search-failure evidence. This intentionally
changes unsafe fallback output; there is no schema or resource migration.

## Review scope

The Scene gate examines all primary planned marks, including point marks, and
all relation paths, excluding legend swatches and snapshot/scenario ghosts.
It reports `E_SCENE_RELATION_THROUGH_MARK` with relation/mark identity. Synthetic
fixtures prove outward first legs and no crossings; corpus zero alone cannot
prove a useful route was retained. Acceptance also checks suppression changes,
unchanged compliant routes and rendered target B.

Not included: relation ordering/S-jog changes (#1109), terminal sliver repair
(#1108), dev B's terminal-none changes (#1105), or reviewer-owned YAML tuning.

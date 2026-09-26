# Architecture Review — Independent Axis Name Tables (#432)

**Decision:** accepted for implementation planning against
[the design](../../design/issue-432-axis-name-table-design-2026-09-26.md)
and [normative specification](../../specification/63-axis-name-tables.md).
**Published design-plan base:** `055ad47f44e02653c1a2c3ec6af6550cfdf2c5e0`.

## Whole-architecture consistency

| Boundary | Review finding |
| --- | --- |
| Project and Calendar | Fiscal starts and interval facts stay Project-owned; table data changes names only. No Project, Snapshot or Actual schema change. |
| Render Context and View | Context locale provides an exact default ID, while View v0.22 may override it per labels tier. Both inputs remain explicit and reviewable. Source-version change follows the published v0.16→v0.17 axis correction precedent. |
| Resource closure | Fixed engine-owned catalog bytes ship in source and wheel; no undeclared local file or host locale. User-supplied tables remain a separate future closure design. |
| Layout and text metrics | Layout formats both trial and final labels from one selected table, measures the finished text, retains thinning/visible-overflow policy, and records the chosen table in typed outcome. |
| Scene and adapters | Neither formats or translates an axis label. Existing Scene text identity and adapter projection remain authoritative. |
| Adjacent presentation | Table-cell locale formatting is separate from axis name-table selection. Font metrics, rotation, axis collision domains, as-of markers, and #426 tier appearance do not gain hidden policy. |
| Diagnostics | Checked catalog equivalences and selected-alias warning prevent a no-op declaration from passing silently. Invalid table data or identity refuses deterministically. |

## Risks and gates

The migration touches View v0.21 resources, immutable Context pins, package
mirrors, schema inventory and public materializers. These changes must be one
materializable implementation publication unit. A partial v0.22 push would
leave contexts invalid and is prohibited. The static audit must compare all
months and year-bearing forms; January-only spot tests are insufficient.
Automatic tiers must use the same table in fitting and final text, or geometry
and output can diverge. Inspect changed SVG as a batch, especially the
Japanese Controller Z slide. Conformance, byte reproduction, full CI and the
literal #432 acceptance table are release gates.

No unresolved responsibility conflict remains. The design is consistent with
the Project → View/resource → Layout → Scene → adapter architecture and
supersedes older locale/Scene wording explicitly rather than preserving it as
an alternate runtime path.

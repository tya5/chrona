# ADR-0031: Constraint-driven Surface Layout is the single geometry authority

- Status: Accepted
- Date: 2026-09-21
- Scope: Issue #58

## Context

Visual inspection of materialized Gantt charts exposed text overlap, duplicate delta labels, poor dependency routes, and invisible group headers. The existing Scene builder measures table columns, chooses label coordinates, calculates group headers, and invokes routing while also emitting primitives. That mixes geometry with semantic-to-primitive projection and allows individually valid elements to form an unreadable surface.

Changing HALCYON YAML alone can reduce density but cannot make an infeasible requested layout safe. Conversely, adding example-specific offsets would create a hidden preset branch.

## Decision

Introduce one internal, immutable **SurfaceLayoutRequest → SurfacePlacement** boundary.

- PresentationContract remains the canonical semantic closure.
- Layout alone measures text, allocates table columns, selects label candidates, reserves group header space, and chooses or rejects relation routes.
- Layout returns completed placements for table cells, plot labels, marks, group headers, relation paths, axis labels and decoration slots, plus ordered diagnostics.
- Scene consumes placements and emits primitives. It does not call font metrics, scale columns, choose label positions, reserve group space, or invoke a router.
- SVG remains a serializer of completed primitives.

A placement is valid only when it satisfies its required constraints. A placement that cannot be made valid follows its declared policy: `diagnose` fails before Scene; `suppress` produces an explicit suppressed optional placement and diagnostic; `ellipsize-with-source` creates a measured ellipsized text placement retaining source provenance. No policy permits overlapping text.

## Consequences

### Positive

- Table, labels, groups and routes share one collision model and one deterministic geometry authority.
- The solution applies to any View/Layout/Theme combination; no example or slide identifier branch exists.
- Snapshot and PNG review can assert geometry from placements instead of reverse-engineering SVG.
- Scene and renderer become materially simpler and testable at a stable handoff.

### Costs

- The current v0.5 Scene builder requires a structural refactor before behavior changes.
- Layout gains typed placement records and shared geometry validation.
- View and Layout schemas gain only the policies that current resources cannot express: label overflow, relation overflow/quality, and group presentation.

## Rejected alternatives

1. **Adjust only HALCYON widths, labels and relations.** It masks but does not diagnose infeasible layouts.
2. **Keep Scene as the layout engine and add collision checks there.** It preserves duplicate geometry authorities.
3. **Allow silent label or relation deletion.** It loses review information without evidence.
4. **Use PowerPoint or manual SVG edits for annotation and layout.** It violates Chrona's standalone generated-output boundary.

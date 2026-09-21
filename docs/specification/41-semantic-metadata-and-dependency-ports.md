# Semantic Metadata and Dependency Ports

**Status:** Design complete — Issue 39
**Depends on:** Specifications 37–40.

## 1. Completed primitive semantics

`ScenePrimitive` is the completed semantic boundary. Builders must construct it with keyword arguments for optional semantic fields. `semantic_facet` describes the temporal/content facet (`planned`, `actual`, `dependency`, `table-cell`); `purpose` describes the consumer-facing purpose (`planned-mark`, `dependency-connector`, `table-cell`, etc.). SVG serializes both verbatim. Renderer adapters never infer either value from a scene ID.

## 2. Dependency ports

Scene computes dependency endpoints from completed planned-mark geometry. A span source port is its planned end; a span target port is its planned start. A point uses its planned point for either endpoint. Port choice is stable for a row/item instance and is computed before routing. Relation expansion across repeated row instances retains these per-instance ports.

## 3. Boundaries

Project supplies semantic relations only. View supplies row/item membership. Scene supplies primitive semantics, mark bounds, ports, and routes. SVG only serializes the completed values. No legacy setting, renderer fallback, title/nearest-edge matching, or project-specific branch is allowed.

## 4. Acceptance

- SVG includes non-empty `data-purpose` for completed primitives;
- dependency x coordinates derive from planned mark endpoints, not the row edge;
- composed row instances retain deterministic port IDs; and
- existing automatic rows remain stable apart from corrected metadata/geometry.

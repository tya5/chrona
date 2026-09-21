# 50. Constraint-driven Gantt Surface Quality

**Status:** Proposed — Issue #58 design
**Depends on:** Specifications 37, 44, 49 and ADR-0031.
**Owns:** the generic feasibility, placement, diagnostics and acceptance contract for a completed Gantt review surface.

## 1. Ownership

| Layer | Owns | Must not own |
| --- | --- | --- |
| Project / Actual | dates, dependencies, calendar, observation facts | visual geometry |
| View | selection, grouping, columns, label/relation intent | coordinates or pixel thresholds |
| Theme | typography and declared numeric metrics | content choices or collision decisions |
| Layout | all measurement, constraints, placement, routing and feasibility | Project semantics or SVG serialization |
| Scene | placement-to-primitive projection and z-order | font measurement or geometric search |
| SVG/PNG | serialization and visual evidence | policy inference |

## 2. Structural refactor

Before any functional change, replace Scene-owned geometry helpers with the following immutable internal values:

- `SurfaceLayoutRequest`: canonical table cells, Review rows/members, axis facts, label requests, relation endpoints, decoration requests, resolved slots, Theme metrics and FontMetrics identity.
- `SurfacePlacement`: table columns/cells, rows/tracks/marks, axis text slots, label placements, group header placements, relation placements, decoration placements and ordered diagnostics.
- `TextPlacement`: source id, content, measured bounds, typography role, overflow result (`fit`, `ellipsized`, or `suppressed`).
- `RelationPlacement`: source/target ports, path, quality measurements, or explicit suppression.

Layout returns only completed placements. Scene accepts `SurfacePlacement` and is prohibited from importing the router or FontMetrics.

## 3. Feasibility contract

### 3.1 Table

For every table column, Layout measures the header and all selected normalized cell strings. A `diagnose` table slot is feasible only when every required cell can receive its measured unbroken bounds inside the table slot with the declared inter-column gap. Layout MUST NOT uniformly shrink columns below those bounds.

For `ellipsize-with-source`, Layout allocates deterministic widths, produces ellipsized `TextPlacement` values, and retains full source text/provenance. For `diagnose`, infeasibility raises `E_LAYOUT_TABLE_OVERFLOW` before Scene. Text bounds from distinct table cells and column headers MUST NOT intersect.

### 3.2 Labels and delta

View label intent becomes:

```yaml
visibility:
  labels:
    placement: plot | table | none
    content: [title, finishDelta]
    side: auto | start | end
    overflow: suppress | diagnose
```

`plot` creates ordered candidates at the eligible mark sides and rejects candidates that intersect required table text, axis text, marks, accepted labels, required annotations, or viewport bounds. `auto` tries start then end in deterministic order. If no candidate fits, the chosen overflow policy applies.

`finishDelta` has exactly one text representation per item. When selected in `labels.content`, no second standalone variance text is emitted. Its semantic role remains derived from the signed value.

### 3.3 Relations

View relation intent becomes `none` or an object with `mode: semantic` and `overflow: suppress | diagnose`. Layout Profile adds `relationRouting.maxBends` and `relationRouting.maxDetourRatio` numeric geometry policy.

Layout routes between completed ports through deterministic orthogonal candidates. A route is acceptable only when it stays in the timeline, avoids required obstacles, has at most `maxBends`, and its Manhattan length is at most `maxDetourRatio × directDistance`. It ranks candidates by crossings, length, bends, then lexicographic points. No acceptable route follows the relation overflow policy. Suppression creates `W_LAYOUT_RELATION_SUPPRESSED`; diagnosis raises `E_LAYOUT_RELATION_UNROUTABLE`.

### 3.4 Groups and legend

View grouping gains `presentation: band | header`; `header` requires a non-zero resolved `timeline.groupHeader.blockSize`. Layout reserves one header block before the group's first row and supplies measured header text bounds spanning the selected table/timeline surface. Missing capacity raises `E_LAYOUT_GROUP_HEADER_OVERFLOW`.

A Layout `legend` slot is the sole authority for legend geometry. When it exists, every selected legend entry emits one swatch and one measured label. When absent, there are no legend primitives. It is a resource choice, not a renderer fallback.

## 4. Schema and normalization

Update View schema/normalizer for the label overflow field, relation object form, and grouping presentation. Update Layout Profile schema/normalizer for relation routing. Preserve legacy `relations: semantic` by ingress-normalizing it to `{mode: semantic, overflow: diagnose}`. Preserve existing boolean or shorthand labels through the existing ingress adapter and normalize before Layout.

No HALCYON identifier, canvas size, role name, or fixture chooses behavior.

## 5. Verification

Before Scene construction, `assert_surface_placement` verifies:

1. required text bounds are inside their slots and pairwise non-intersecting;
2. table, axis, label, group header and legend placements satisfy their selected overflow policy;
3. every accepted relation route meets its quality limits;
4. no semantic item has duplicate finish-delta text;
5. every present slot family has its required placements.

Tests cover each invariant with one neutral fixture and HALCYON regressions. Materializer byte checks remain required. PNG evidence at declared viewports is reviewed from generated output, never hand-edited.

## 6. Migration

1. introduce internal request/placement records and migrate the current table/row/mark/axis geometry without behavioral change;
2. move label, relation, group and legend geometry out of Scene;
3. add feasibility diagnostics and schema normalization;
4. adapt non-HALCYON fixtures and current examples; and
5. regenerate expected SVG only through the public materializer after all automated and visual acceptance checks pass.

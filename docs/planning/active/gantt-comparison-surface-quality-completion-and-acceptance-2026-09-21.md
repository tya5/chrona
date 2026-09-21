# Gantt Comparison Surface Quality — Completion and Acceptance Design

**Status:** D58-2 through D58-4 design complete; implementation is not authorized by this document.
**Issue:** #58

## 1. Change inventory

| Requirement | Owner | Current defect | Design artifact | Future implementation seam |
| --- | --- | --- | --- | --- |
| Feasible table text | Layout | `place_table_columns` scales below measured width | Spec 50 §3.1 | `SurfaceLayoutRequest` / `SurfacePlacement` |
| Non-overlapping plot labels | View + Layout | Scene directly places labels | Spec 50 §3.2 | label candidate solver |
| One delta text | PresentationContract + Scene | Scene emits requested label and implicit variance | Spec 50 §3.2 | canonical label requests |
| Readable relations | View + Layout | route existence is mistaken for route quality | Spec 50 §3.3 | relation placement solver |
| Visible group headers | View + Layout + Theme | Scene derives geometry and header metric is implicit | Spec 50 §3.4 | group placement |
| Legend | Layout + Scene | only a present slot emits it | Spec 50 §3.4 | decoration placement |
| Generated visual acceptance | Materializer | byte identity alone | this document §3 | PNG evidence runner |

## 2. Fixtures

| Fixture | Purpose | Required proof |
| --- | --- | --- |
| `surface_quality_table_overflow` | narrow table with unbreakable normalized values | `E_LAYOUT_TABLE_OVERFLOW`, no Scene |
| `surface_quality_table_ellipsize` | same content with ellipsize policy | measured non-overlapping ellipsized placements with source provenance |
| `surface_quality_labels` | dense marks with title/delta | deterministic accepted placement or declared suppression; never duplicate delta |
| `surface_quality_relations` | crossing and long-detour dependencies | best acceptable path, suppression warning, and diagnose failure variants |
| `surface_quality_groups_legend` | grouped rows and legend slot | header text bounds plus role-derived swatch/label placement |
| `halcyon-1` | three current contexts | no overlap invariant; explicit label/relation/header/legend YAML choices |

All neutral fixtures are resource-driven and may not import or name HALCYON.

## 3. Acceptance matrix

| ID | Required evidence |
| --- | --- |
| A58-01 | Structural refactor: Scene receives placements and has no FontMetrics/router import. |
| A58-02 | Table feasibility tests prove no intersecting table header/cell text. |
| A58-03 | Label candidate tests prove bounds do not intersect protected geometry and delta is unique. |
| A58-04 | Relation tests prove quality scoring, suppression and diagnosis. |
| A58-05 | Group/legend tests prove present slots emit full families and missing capacity diagnoses. |
| A58-06 | Schema/normalization tests cover all new forms and legacy aliases. |
| A58-07 | Full pytest and all conformance suites pass. |
| A58-08 | Public materializer reproduces every example byte-for-byte after reviewed regeneration. |
| A58-09 | PNG evidence for three HALCYON contexts and neutral fixtures is visually reviewed at declared viewport. |

## 4. Compatibility and YAML migration

Existing `labels` and `relations: semantic` authoring forms are preserved by one ingress normalization path. Existing resources retain their former required behavior until they explicitly choose `suppress`; a chart that is now infeasible correctly diagnoses rather than overlap.

HALCYON changes are limited to resource declarations after A58-01 through A58-06 are implemented:

- Mission brief and Launch campaign select `labels.overflow: suppress` or table labels as determined by the completed acceptance fixture.
- They select relation overflow explicitly.
- Programme board declares `grouping.presentation: header` and a Theme group-header metric only if its visual review needs headings.
- Layout Profiles add a legend slot only where a legend is a reader need.

These are examples of public general declarations, not code branches.

## 5. Release guard

No expected SVG, PNG evidence, or YAML is updated until all relevant focused tests, full pytest and public materializer checks pass. Any failed visual invariant returns to D58-2/3 before implementation continues.

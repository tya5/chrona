# Current work record — data-only lane membership (#467, #494)

**Public base:** `fa2db029` on `main`. Units A–C, including the typed Layout→Scene handoff and #494 route correction, are published. Unit D resource migration, lane activation and acceptance evidence are under verification, not yet published. The issue body and latest owner comments govern; superseded proposals remain in Git history.

## Design plan and selected contract

Use cases: group tasks and attached milestones share predictable lanes; an author may opt into chain/date packing, while `automatic` remains available. The open decisions—membership authority, collision response, label fallback, typed Scene provenance, route-label precedence and visible facets—are resolved in [Spec 38](../../specification/38-review-row-composition.md), [Spec 50](../../specification/50-constraint-driven-gantt-surface-quality.md), and the [B3 handoff design](../../design/issue-467-b3-typed-lane-scene-handoff-correction-2026-09-27.md). No optional leader/rotation or local aesthetic tuning is part of this release.

Whole-architecture review: Project dates/relations and View declarations determine immutable membership before Theme or geometry. Layout owns subtracks, exact facet overlays, text/icon measurement, suppression, and routes; Scene projects the typed completed emission inventory; adapters only serialize. Global title icons are not lane members. A View-omitted `missingActual` facet is absent from Layout preflight through SVG. Actual progress overlays only its own combined instance's planned facet. These rules do not change non-lane behavior; deliberate View v0.28 migration is documented in Spec 38. The adjacent [B3 architecture review](../../reviews/current/issue-467-b3-typed-lane-scene-handoff-architecture-review-2026-09-27.md) and Specs 09/24/33/46/64 were checked before code.

## Literal #467 acceptance

- [ ] `rows.mode: lanes` has ordered `rows.packing` from `explicit`, `attached`, `chain`, `dates`; default `[explicit, attached]`. Explicit keys share a lane; attached points use their host; opt-in chain/date rules use planned intervals with touching allowed; otherwise an item opens its own lane.
- [ ] Membership is rendering-independent: two Themes differing in font, measured label width, icons and strokes have identical Scene membership; a Project/View-only oracle agrees.
- [ ] Assignment is deterministic and stable under insertion outside a lane.
- [ ] Every packed name and selected delta is placed by the shared label model or suppressed and counted; labels never add lanes.
- [ ] On 02 with `[explicit, attached, chain, dates]`, `structure → avionics → bus-test` shares one lane; acceptance lists membership per group and checks the data-only oracle.
- [ ] `automatic` remains byte-identical; transit-map presets explicitly opt into chain/dates, and defaults do not.
- [ ] At least three committed slides use reproducible lanes.

## Literal #494 acceptance

- [ ] On lane-mode 02, no relation is suppressed for `egress-collision`; every other suppression has a measured cause.
- [ ] On 02/11/12, no route crosses a required lane or member label.
- [ ] Report and attribute any 02 lane-count or membership change.

## Implementation and publication plan

| Unit | Owner and publication gate |
| --- | --- |
| A–B1, published | View v0.28 schema and pure membership kernel; Review lane/table projection. Data-only oracle, key/interval and stability tests. |
| B2–B3, published | Fixed-lane Layout preflight/composition and typed emission inventory; Scene projects exact marks, icons, labels and obstacles. Focused facet, suppression, repeated-instance, Theme and non-lane byte tests. |
| C, published | Layout route search and measured suppression evidence. #494 02/11/12 crossing and cause tests. |
| D, current | Migrate bundled default/catalogue Views and at least three public slides; retain 01 Mission Brief as an unchanged automatic/table witness and Editorial Reference separately from the new Editorial lane variant. Activate public lanes, regenerate Scene/SVG and derived reports as one batch. Focused tests, public materializer check, conformance, artifact review, then one serial push and CI matrix. |
| Acceptance | Publish a concise review with every literal row above, exact commit/CI links, 02 membership per group, visible/suppressed counts, generated differences and architecture findings. Close #467/#494 only when all rows and release gates pass. |

Current local evidence: 217 focused tests passed before the final icon-handoff and 01-preservation adjustments; the two-Theme integration regression and 29-slide regeneration also pass. Re-run affected focused checks and the generated-report checks on the final tree. CI supplies full three-OS pytest/conformance, wheel/smoke and newest-Python materializer evidence after D publication. An unexpected remote update or red required gate pauses closure.

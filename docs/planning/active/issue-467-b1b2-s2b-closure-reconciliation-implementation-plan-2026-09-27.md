# Current work record — data-only lane membership (#467, #494)

**Accepted public base:** `f3688940` on `main`; the [release review](../../reviews/current/issue-467-494-lane-acceptance-review-2026-09-27.md) is published. Units A–D include typed Layout→Scene handoff, #494 routing, lane resource migration, and 29 public slides. The three-OS and newest-Python CI gate passed in [run 36328250874](https://github.com/tya5/chrona/actions/runs/36328250874). The issue body and latest owner comments govern; superseded proposals remain in Git history.

## Design plan and selected contract

Use cases: group tasks and attached milestones share predictable lanes; an author may opt into chain/date packing, while `automatic` remains available. The open decisions—membership authority, collision response, label fallback, typed Scene provenance, route-label precedence and visible facets—are resolved in [Spec 38](../../specification/38-review-row-composition.md), [Spec 50](../../specification/50-constraint-driven-gantt-surface-quality.md), and the [B3 handoff design](../../design/issue-467-b3-typed-lane-scene-handoff-correction-2026-09-27.md). No optional leader/rotation or local aesthetic tuning is part of this release.

Whole-architecture review: Project dates/relations and View declarations determine immutable membership before Theme or geometry. Layout owns subtracks, exact facet overlays, text/icon measurement, suppression, and routes; Scene projects the typed completed emission inventory; adapters only serialize. Global title icons are not lane members. A View-omitted `missingActual` facet is absent from Layout preflight through SVG. Actual progress overlays only its own combined instance's planned facet. These rules do not change non-lane behavior; deliberate View v0.28 migration is documented in Spec 38. The adjacent [B3 architecture review](../../reviews/current/issue-467-b3-typed-lane-scene-handoff-architecture-review-2026-09-27.md) and Specs 09/24/33/46/64 were checked before code.

## Literal #467 acceptance

- [x] `rows.mode: lanes` has ordered `rows.packing` from `explicit`, `attached`, `chain`, `dates`; default `[explicit, attached]`. Explicit keys share a lane; attached points use their host; opt-in chain/date rules use planned intervals with touching allowed; otherwise an item opens its own lane.
- [x] Membership is rendering-independent: two Themes differing in font, measured label width, icons and strokes have identical Scene membership; a Project/View-only oracle agrees.
- [x] Assignment is deterministic and stable under insertion outside a lane.
- [x] Every packed name and selected delta is placed by the shared label model or suppressed and counted; labels never add lanes.
- [x] On 02 with `[explicit, attached, chain, dates]`, `structure → avionics → bus-test` shares one lane; acceptance lists membership per group and checks the data-only oracle.
- [x] `automatic` remains byte-identical; transit-map presets explicitly opt into chain/dates, and defaults do not.
- [x] At least three committed slides use reproducible lanes.

## Literal #494 acceptance

- [x] On lane-mode 02, no relation is suppressed for `egress-collision`; every other suppression has a measured cause.
- [x] On 02/11/12, no route crosses a required lane or member label.
- [x] Report and attribute any 02 lane-count or membership change.

## Implementation and publication plan

| Unit | Owner and publication gate |
| --- | --- |
| A–B1, published | View v0.28 schema and pure membership kernel; Review lane/table projection. Data-only oracle, key/interval and stability tests. |
| B2–B3, published | Fixed-lane Layout preflight/composition and typed emission inventory; Scene projects exact marks, icons, labels and obstacles. Focused facet, suppression, repeated-instance, Theme and non-lane byte tests. |
| C, published | Layout route search and measured suppression evidence. #494 02/11/12 crossing and cause tests. |
| D, accepted | Bundled default/catalogue Views and five public lane slides are published; 01 Mission Brief remains an unchanged automatic/table witness and Editorial Reference remains separate. Lane visual binding, migrated tests, generated reports, all 29 public materializers and the three-OS CI matrix pass. |
| Acceptance, published | The release review records every literal criterion, exact commit/CI, 02 membership, visible/suppressed counts, generated differences and architecture findings. |

Release evidence is in the linked review; no local-only result is counted as completion. Optional visual tuning remains in #501/#502.

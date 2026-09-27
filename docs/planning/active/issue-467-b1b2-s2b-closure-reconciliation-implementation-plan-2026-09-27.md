# Current work record — data-only lane membership (#467, #494)

**Status:** design and implementation plan complete; implementation pending. This record supersedes its geometry-first content; Git retains the earlier text. Public `main` accepts `rows.mode: lanes` but keeps rendering guarded. The issue's 2026-09-27 10:58 UTC owner decision is the current acceptance authority. The next View contract will be v0.28; older v0.27 resources are migrated explicitly.

## Literal #467 acceptance

- [ ] A lane row mode exists with a declared packing policy, `rows.packing`: an ordered subset of `explicit`, `attached`, `chain`, `dates`. The default is `[explicit, attached]`.
  - `explicit`: items the View or Project assigns to the same lane key share it.
  - `attached`: a point that `attachesTo` a span sits on its host's lane (#486).
  - `chain` (opt-in): a finish-to-start successor continues on its predecessor's lane when their date intervals do not overlap.
  - `dates` (opt-in): remaining items in a group, in date order, take the first lane whose date intervals do not overlap; touching is allowed.
  - Items no rule places get their own lane.
- [ ] Membership never depends on rendering: the same Project/View with two Themes differing in font, label length, icons and stroke widths yields identical membership; a data-only Project/View derivation matches the Scene.
- [ ] Assignment is deterministic and stable: inserting one item does not reorder lanes it does not join.
- [ ] Labels fit lanes, not vice versa. Every packed name and selected delta uses the #466/#488 model (end, start, stagger or leader); an unplaceable name is suppressed and counted and never adds a lane.
- [ ] On `02-programme-board`, `packing: [explicit, attached, chain, dates]` keeps `structure → avionics → bus-test` on one lane. Acceptance lists membership per group and proves the data-only derivation.
- [ ] `automatic` remains byte-identical. Transit-map presets explicitly declare `chain`/`dates`; default packing implies neither.
- [ ] At least three committed slides use lanes with reproducible evidence.

## Related #494 gate

On lane-mode 02, no relation is suppressed for `egress-collision`; every remaining suppression has a measured cause. Routes on 02, 11 and 12 never cross required lane/member labels. Any 02 membership/count change from prior evidence is attributed. #494 route behavior is downstream of, and cannot choose, #467 membership.

## Selected design and whole-architecture review

Spec 38 now owns the exact key, interval, precedence, identity, suppression and migration rules. The View chooses a Project object field and/or target-specific keys; its explicit map wins. This supports Project-supplied domain data without adding presentation policy to the Project schema. Packing is a canonical-order subset, so attachment closure precedes chain/date placement. Planned half-open intervals alone decide compatibility; Actual, comparison and Theme never decide membership. Explicit overlap is authored intent and may require inner Layout tracks. Unknown targets, malformed keys and conflicting attached keys fail closed.

Against Specs 09/24/38/46/50/64: schedule and View selection remain upstream of a pure Review membership result; Layout receives fixed membership and owns all measured geometry, labels, obstacles and routes; Scene transports membership and completed primitives; adapters serialize. Existing mark/icon footprint work remains useful only after membership. The Scene pairwise non-redundancy audit is removed from #467 acceptance, while Scene membership identity and #494 obstacle/route evidence remain. No renderer, Theme or Project scheduling contract changes. The deliberate incompatibility is View v0.28's new `rows.packing`/`rows.laneKeys`; automatic/explicit outputs stay byte-identical. The main risk is dense authored keys: verify internal track height, label suppression counts and route corridors without feeding any of them back into membership.

## Implementation and publication units

| Unit | Owners and migration | Acceptance before serial push |
| --- | --- | --- |
| **A. Data-only membership** | `schemas/view-v0.28.schema.yaml` and package mirror, resource registry/parser, `presentation.review` membership model, projection adapter and focused tests. Add `packing` and `laneKeys`; derive lane IDs, member IDs and placement-rule evidence solely from Project/View facts. Remove geometry-first allocation from the membership API; retain its obstacle utilities only for later placement. Guard remains closed. | Schema/conformance, unknown/conflicting key and rule-order diagnostics, planned interval/point/attachment/chain/date tests, data-only 02 oracle and inserted-item stability. No Theme, font, icon, stroke, Actual or Scene dependency in this module. |
| **B. One-plan placement and Scene** | `usecases/render_review.py`, `layout/surface_composer.py`, lane placement helpers, `scene/v05_builder.py`, Scene model/serializer/schema and focused tests. Feed A's immutable membership into measured row/table/mark/label closure; reuse typed facets/icons only after membership. Place names/deltas by the shared label model; suppress/count failures without reallocating. Preserve lane member provenance in Scene. Keep one owner on `surface_composer.py`; guard closed until direct hidden 02/11/12 output is correct. | Same Scene membership under two strongly different Themes, equal to the data-only oracle; completed labels/icons and table/group bounds; no lane changes from geometry; automatic/explicit Scene/SVG bytes unchanged; public materializers checked as a batch. |
| **C. #494 routes** | Layout route search/cause producer, Scene diagnostics and isolated route tests; no allocator edits. Integrate existing read-only no-crossing helper only when the lane Scene is emitted. | On 02, no `egress-collision` suppression; every remaining suppression has typed measured cause. On 02/11/12, no route crosses placed required labels. Report any membership/count difference from pre-pivot branch evidence. |
| **D. Resources and release** | Migrate bundled default, catalogue Views and at least three committed slide Views to v0.28; explicitly choose `chain`/`dates` only for transit-map presets. Review the separately staged YAML candidate against the new policy before using it. Regenerate public Scene/SVG/materializer evidence and activate lane rendering once A–C pass. | Rendered 02 chain and per-group membership list, visible/suppressed name and delta accounting, three reproducible lane slides, unchanged automatic bytes, batch SVG/Scene diff review and three-OS CI full pytest/conformance + wheel/smoke + newest-Python materializer gate. Publish final acceptance review with a row for every literal #467/#494 criterion, then close only when all are met. |

Each unit is independently reviewed and published. Before each push, fetch `origin/main`, inspect ahead/behind, target commits, staged/generated diffs and conflict risk; never force. Focused tests run locally in the project venv, while CI supplies the costly full matrix. If implementation reveals a missing contract, update Spec 38/adjacent living specs and this record, publish the correction, then resume. The old pairwise Scene audit is not an acceptance gate; its code may remain only if it serves a justified post-membership diagnostic.

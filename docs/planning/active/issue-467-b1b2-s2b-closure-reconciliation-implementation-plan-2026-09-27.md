# Current work record — data-only lane membership (#467, #494)

**Status:** design complete; implementation plan pending. This record supersedes its geometry-first content; Git retains the earlier text. Public `main` accepts `rows.mode: lanes` but keeps rendering guarded. The issue's 2026-09-27 10:58 UTC owner decision is the current acceptance authority. The next View contract will be v0.28; older v0.27 resources are migrated explicitly.

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

## Design questions and boundaries

1. Define the public lane-key field, scope, duplicate/unknown-key behavior, and explicit grouping when Project and View both contribute; no invented coordinate or Theme input.
2. Define half-open date intervals, point/touching semantics, source variants, missing dates and deterministic tie-breaking. Resolve precedence/conflicts among ordered `explicit`, `attached`, `chain`, `dates`, including attached points and repeated objects.
3. Separate a data-only membership result from Layout's later measured row height, mark, label/icon, obstacle and relation placement. Scene carries membership provenance; adapters serialize only. Decide whether existing footprint/facet inventories remain for label and #494 diagnostics, and remove obsolete pairwise non-redundancy acceptance.
4. Define label suppression/count, delta behavior, lane table cells and group headers after membership. Preserve `automatic` bytes; choose the next View schema version and resource migration. Existing unpushed geometry-first helper and YAML candidate are not release evidence.
5. Review against Specs 09/24/38/46/50/64, #486 attachment semantics, #466/#488 placement and #494 routing. Record intentional incompatibilities, failure diagnostics and extension points in living specs, not repeated here.

## Selected design and whole-architecture review

Spec 38 now owns the exact key, interval, precedence, identity, suppression and migration rules. The View chooses a Project object field and/or target-specific keys; its explicit map wins. This supports Project-supplied domain data without adding presentation policy to the Project schema. Packing is a canonical-order subset, so attachment closure precedes chain/date placement. Planned half-open intervals alone decide compatibility; Actual, comparison and Theme never decide membership. Explicit overlap is authored intent and may require inner Layout tracks. Unknown targets, malformed keys and conflicting attached keys fail closed.

Against Specs 09/24/38/46/50/64: schedule and View selection remain upstream of a pure Review membership result; Layout receives fixed membership and owns all measured geometry, labels, obstacles and routes; Scene transports membership and completed primitives; adapters serialize. Existing mark/icon footprint work remains useful only after membership. The Scene pairwise non-redundancy audit is removed from #467 acceptance, while Scene membership identity and #494 obstacle/route evidence remain. No renderer, Theme or Project scheduling contract changes. The deliberate incompatibility is View v0.28's new `rows.packing`/`rows.laneKeys`; automatic/explicit outputs stay byte-identical. The main risk is dense authored keys: verify internal track height, label suppression counts and route corridors without feeding any of them back into membership.

## Design and publication order

- **D1 — membership contract:** resolve questions 1–2 in Spec 38 and the View schema design; publish the normative design and whole-architecture review before code.
- **D2 — presentation contract:** resolve questions 3–4 with Specs 46/50/64 and #494; publish the design.
- **I-plan:** update this record with reviewable data-only allocator, placement, route and resource slices; name owned files, tests, public materializers, generated evidence and CI gates. Publish before product code.
- **Implementation:** retire geometry inputs from membership, then wire the data-only result to Layout/Scene, adapt labels/routes, migrate resources and validate three slides. Keep the lane render guard closed until the end-to-end gate passes. Publish coherent tested units serially.
- **Acceptance:** compare Scene membership with a Project/View-only oracle, Theme invariance, rendered names/deltas/route evidence, unchanged automatic bytes, batch SVG/Scene diffs and three-OS CI. Record every literal criterion once in the final review; close only after public evidence is complete.

Old geometry-first allocation, preflight and Scene pairwise audit are not accepted merely because they exist on `main`. Reuse their geometry closure only where it serves post-membership placement or route evidence.

# #467 / #494 lane release acceptance — 2026-09-27

**Product commit:** `f3688940` on `main`. **Plan:** [current #467 record](../../planning/active/issue-467-b1b2-s2b-closure-reconciliation-implementation-plan-2026-09-27.md). **CI:** [run 36328250874](https://github.com/tya5/chrona/actions/runs/36328250874) passed: conformance, pytest and wheel on macOS/Ubuntu/Windows, plus newest-Python public materializer reproduction.

The release candidate passed focused lane/visual tests (including two Theme variants, label and mark icons), the migrated CI-failure tests, three generated-report checks, and a batched 29-slide public materializer check. SVG images for 02, 03, 12 and 16 were inspected. Only existing 02/03/11/12 Scene+SVG pairs changed in Unit D; 16 is new. The other 24 existing pairs, including automatic 01/08/09, are byte-identical. `f3688940` changed no public Scene/SVG bytes, and refreshed derived contrast, font and diagnostic reports. Exact Layout→Scene emission ownership and the View-selected `missingActual` mark are closed before serialization; global title icons remain outside lane member inventory. Layout alone measures and places; Scene and adapters do not re-decide membership or routes. This matches Specs 38/50/64 and the adjacent architecture review.

## Literal acceptance

| Criterion | Status and direct evidence |
| --- | --- |
| #467 ordered `explicit`/`attached`/`chain`/`dates`, default `[explicit, attached]`, with declared-key, attachment, half-open chain/date and own-lane rules | Met: `tests/unit/chrona/presentation/test_lane_membership.py`; `tests/integration/test_view_v01_schema.py`; package Views declare opt-in rules only where intended. |
| #467 Theme-independent and data-only Scene membership | Met: `tests/integration/test_lane_theme_handoff.py` changes font, measured label widths, icon bounds, stroke widths and glyphs; `test_public_lane_layout_projects_fixed_membership` compares Scene with the Project/View-only oracle. |
| #467 deterministic insertion stability | Met: `test_inserting_unrelated_item_preserves_existing_lane_ids`. |
| #467 every packed name/selected delta visible or suppressed-and-counted, with no added lane | Met: public 02 has 26 members, 12 visible name labels and 14 `W_LAYOUT_LABEL_SUPPRESSED` warnings with `I_LAYOUT_PLOT_LABELS_SUPPRESSED:count=14`; seven visible names include signed deltas. Membership remains eight lanes. 03 has 12/12 visible, 16 has 26/26. |
| #467 02 named chain and membership by group agree with data-only derivation | Met: 02 has eight lanes, listed below; `structure → avionics → bus-test` shares the bus/PDR lane. Kernel and public Scene oracle tests pass. |
| #467 `automatic` unchanged and transit-map packing opt-in | Met: automatic 01/08/09 and all other unaffected public pairs are byte-identical; `test_lane_resource_migration_inventory_and_editorial_mirror` checks preset declarations. |
| #467 at least three reproducible committed lane slides | Met: 02, 03, 11, 12 and new 16 are committed; the 29-slide materializer batch and newest-Python CI reproduction pass. |
| #494 zero 02 `egress-collision` suppression and measured causes for any remainder | Met: 24 dependency primitives, zero suppressed relations and hence zero unaccounted causes on 02. `test_public_lane_layout_projects_fixed_membership` checks cause accounting. |
| #494 no route through required labels on 02/11/12 | Met: `test_public_lane_scene_routes_never_cross_required_lane_or_member_labels` renders all three public closures and checks every Scene dependency segment against visible lane/table/group/member-label bounds. The earlier citation to a nonexistent test was incorrect. |
| #494 02 membership/count unchanged or attributed | Met: eight data-only lanes now; the earlier nine-lane figure was a geometry-first pre-pivot estimate. The owner-approved Project/View-only interval rules and published `avionics→bus-test` 4wd lag explain this release membership. No D/Theme/label feedback changes membership. |

02 membership by group (one line per lane): bus `eps, cdr` / `pdr, structure, avionics, bus-test`; payload `optics, detector, payload-tvac, payload-delivery`; AIT `integration, vibration, tvac, emc, psr`; ground `mcs, comms-test` / `station`; launch `launch-contract, shipment, campaign, frr, launch`; operations `rehearsals, leop, first-light`.

Visual tuning is deliberately separate: #502 covers the blank group-less lane table on 03, while #501 owns default label-distance/fill concerns. Neither changes the literal #467/#494 membership or routing gate.

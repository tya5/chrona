<!-- chrona:literal-acceptance/v1 -->

# Issue 1841 — trial regression acceptance review

Current plan/design and status: [issue comment 6295885856](https://github.com/tya5/chrona/issues/1841#issuecomment-6295885856). Normative contracts: [Spec 08](../../specification/08-scene-and-rendering.md), [Spec 30](../../specification/30-shared-presentation-foundation.md), and [Spec 50](../../specification/50-constraint-driven-gantt-surface-quality.md). Row 4 corrections and implementation plan preceded source; paired-fragment receipt correction is published in [commit 2da86f605](https://github.com/tya5/chrona/commit/2da86f6056475f60be310f9caff75d07dcd45780).

Current source [38445416f](https://github.com/tya5/chrona/commit/38445416f) passes 214 focused identity/observer/route/label tests and 135 CLI characterization tests. Layout supplies actual fragment IDs; markerless pairs work, while conflicting/malformed evidence and true duplicates remain findings. One 116-case CLI capture changes only five successful render stdout records, not exits, stderr or generated-file inventories; incidental argparse quote spelling is retained. Final corpus, visual acceptance and release remain pending.

```sh
.venv/bin/python -m pytest -q \
  tests/unit/chrona/presentation/model/test_relation_resolution_info.py \
  tests/unit/chrona/presentation/scene/test_perceptibility.py \
  tests/unit/tools/test_routing_performance_evidence.py \
  tests/integration/test_relation_resolution_wiring.py \
  tests/integration/test_neutral_point_route_label_recovery_1627.py \
  tests/unit/chrona/presentation/layout/test_presentation_labels.py \
  tests/unit/chrona/presentation/layout/test_member_label_required_phase.py
.venv/bin/python -m pytest -q tests/cli/test_cli_characterization.py
```

| # | Literal acceptance criterion | Disposition | Evidence |
| ---: | --- | --- | --- |
| 1 | hints validate against the completed host geometry whatever the primitive kind. On the trial input, hinted renders accept the unchanged routes and the time drops (before/after recorded). | met | [Host and previous-scene controls](../../../tests/unit/chrona/usecases/test_previous_scene.py), [normal backroute controls](../../../tests/unit/chrona/presentation/scene/test_relation_entry_back_route.py); released on review-containing main [`4e779217`](https://github.com/tya5/chrona/commit/4e779217) with [CI 39553831077](https://github.com/tya5/chrona/actions/runs/39553831077). |
| 2 | one shared measure/place rounding for every content-width text; a synthetic case for cells and headers. | met | [Forward-fit tests](../../../tests/unit/chrona/presentation/layout/test_table_forward_fit.py) cover headers/cells and fractional boundaries; released on review-containing main [`4e779217`](https://github.com/tya5/chrona/commit/4e779217), [CI 39553831077](https://github.com/tya5/chrona/actions/runs/39553831077). |
| 3 | the title is honoured; the guide example runs on the default preset in the docs tests. | met | [Heading tests](../../../tests/integration/test_network_heading_parts.py) and [guide execution test](../../../tests/integration/test_network_view_guide.py); released on review-containing main [`4e779217`](https://github.com/tya5/chrona/commit/4e779217), [CI 39553831077](https://github.com/tya5/chrona/actions/runs/39553831077). |
| 4 | a route segment may not run along a mark's edge (treat edge contact as an obstacle); a synthetic case. | not met | [Closed-contact controls](../../../tests/unit/chrona/presentation/layout/test_primary_mark_closed_contact.py) and [endpoint geometry tests](../../../tests/unit/chrona/presentation/layout/test_relation_endpoint_geometry.py). Focused 188-test route/label batch and four HALCYON CLI modes passed at [`9dc1c81f9`](https://github.com/tya5/chrona/commit/9dc1c81f906755f8f1be6c424da7ba30cba028aa); official final corpus/SVG evidence is pending. |
| 5 | network rank placement keeps unchanged nodes (hint or stable ordering), and row pitch is quantised so rows above an insertion stay byte-identical. | met — approved contract | Reviewer decision [6297232443](https://github.com/tya5/chrona/issues/1841#issuecomment-6297232443) retains fractional authored pitch/fill redistribution and permits rank-demand movement; no rounding, network hints, or preset tuning. See [Spec 33 §13.1](../../specification/33-intent-oriented-layout.md) and [Spec 50 §17.2](../../specification/50-constraint-driven-gantt-surface-quality.md). |
| 6 | a route's horizontal extent stays within its endpoints' times plus the port leads, unless it is diagnosed as recovery. | not met | [Temporal-hull tests](../../../tests/unit/chrona/presentation/layout/test_relation_endpoint_geometry.py) cover nominal anchors and outward leads; protected-domain controls are in [test_protected_finite_route_domain.py](../../../tests/unit/chrona/presentation/layout/test_protected_finite_route_domain.py). The neutral 31-relation/22-name/five-arrival fixture and four CLI modes at [`9dc1c81f9`](https://github.com/tya5/chrona/commit/9dc1c81f906755f8f1be6c424da7ba30cba028aa) are focused evidence only; official trial 16 and final corpus evidence remain pending. |

The row 4/6 design keeps completed geometry and route validation in Layout; protected recovery and typed fragment receipts remain explicit and Scene evidence passive. The receipt correction's pre-code authority and plan are [Specs 08/50](https://github.com/tya5/chrona/commit/2da86f6056475f60be310f9caff75d07dcd45780) and [issue comment 6329315913](https://github.com/tya5/chrona/issues/1841#issuecomment-6329315913). Reviewer [6301579399](https://github.com/tya5/chrona/pull/1849#issuecomment-6301579399) accepts only optional relation-name omission, not six member-name omissions or Sunday's detached tail. Fresh trial 12 hint/timing evidence, trial 16 output, restored six HALCYON names/Sunday tail, official final snapshot review, and exact review-containing main three-OS release remain required. Keep issue open until those gates pass.

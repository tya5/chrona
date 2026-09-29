<!-- chrona:literal-acceptance/v1 -->

# #486 attached milestones — acceptance review

**Public base:** `a3bd7c57` on `main` ([implementation PR #511](https://github.com/tya5/chrona/pull/511), [example PR #517](https://github.com/tya5/chrona/pull/517), [visual evidence PR #518](https://github.com/tya5/chrona/pull/518)). **Issue observed:** 2026-09-28, [#486](https://github.com/tya5/chrona/issues/486). **Release CI:** [#518 run 36358406815](https://github.com/tya5/chrona/actions/runs/36358406815) passed newest-Python reproduction plus Ubuntu, macOS and Windows conformance, full pytest and wheel steps.

## Literal issue acceptance

### Issue #486

- Source: [Issue #486](https://github.com/tya5/chrona/issues/486)
- Observed: 2026-09-28

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | The Project schema accepts `attachesTo` on point objects; the validation errors and the outside-span warning are covered by tests. | met | [Project tests](../../../tests/unit/chrona/core/test_attachments.py) cover four errors, outside-span warning and render warning. | — |
| 2 | Attachment changes no scheduled date. A test compares schedules with and without it. | met | [Schedule equality test](../../../tests/unit/chrona/core/test_attachments.py) compares the same Project with and without attachment. | — |
| 3 | A View draws an attached milestone on its host's row, both with and without #467 lanes, and `points: own-row` restores its own row. | met | [Rendered integration tests](../../../tests/integration/test_attached_milestones.py) assert automatic host row, lane owner, `own-row` and lane packing opt-out. | — |
| 4 | The milestone's name and date stay visible, and its delta if it has one. | met | The rendered [Scene and SVG test](../../../tests/integration/test_attached_milestones.py) asserts complete title/date labels and point delta, plus no intersection of the example's Actual mark with its label. The published sample reads `Readiness review · 30 Sep · +8d` and `Range clearance · 12 Oct` in SVG. [Projection](../../../src/chrona/presentation/model/projection.py) derives point `atDelta`; [View](../../../src/chrona/presentation/review/v05_content.py) supplies the content; [Layout](../../../src/chrona/presentation/layout/surface_composer.py) never suppresses attached facts. | — |
| 5 | One committed example has a long task with at least two intermediate milestones attached. HALCYON-1's `campaign` or `mcs` would serve. | met | The [reusable Project](../../../examples/attached-milestones/project.yaml) contains one fixed-span campaign and two internal gates, with [render instructions](../../../examples/attached-milestones/README.md) and an [Actual Set](../../../examples/attached-milestones/actual.yaml). The integration test renders it. HALCYON was an option, not a requirement; keeping it unchanged preserves existing relation visibility. | — |

## Programme-level criteria (optional)

None.

## Verification and architecture

Focused tests: `pytest tests/integration/test_attached_milestones.py -q` (5 passed), its final committed-example visual check (1 passed after #518), `pytest tests/unit/chrona/core/test_attachments.py -q` (7 passed), and `pytest tests/unit/chrona/presentation/model/test_projection_rows.py tests/unit/chrona/presentation/layout/test_surface_quality.py -q` (45 passed). `tools/check_example_reachability.py`, `tools/diagnostic_inventory.py --check`, and `tools/regenerate_public_examples.py --check --jobs 4` passed; all 29 prior public materializers remain byte-identical. The final SVG was also rasterized and inspected: both labels and `+8d` are readable, with separate point marks. A prior #511 CI run had all full pytest tests passing but stale generated diagnostic line anchors; [PR #514](https://github.com/tya5/chrona/pull/514) regenerated the inventory. The final #518 release run is green on every required job.

The Project attachment does not enter scheduling or WBS. View owns active row/lane membership and label facts; Layout measures and places them, with an explicit visible-overflow outcome if necessary; Scene and SVG project completed placements. The independent example avoids altering HALCYON's shared Project, other slide memberships and routes. No unrelated output diff was found. All five literal rows and the release gate are met; #486 is accepted for closure.

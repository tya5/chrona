<!-- chrona:literal-acceptance/v1 -->

# Issue #788 — a gate derived from its dependencies: acceptance review

Source: [Issue #788](https://github.com/tya5/chrona/issues/788), observed 2026-10-02 (body plus one owner comment, last updated 2026-10-01T16:21:28Z). The issue has one acceptance checkbox with two alternatives and a test clause, and a "Decide" section with two options; the table gives each its own row. Design pack: [design plan](../planning/issue-788-derived-gate-design-plan-2026-10-01.md), [design](../../design/issue-788-derived-gate-design-2026-10-01.md), [architecture review](issue-788-derived-gate-architecture-review-2026-10-01.md), [implementation plan](../planning/issue-788-derived-gate-implementation-plan-2026-10-01.md); living contracts [Spec 04](../../specification/04-scheduling-model.md) section 20.4, [Spec 05](../../specification/05-project-format.md), [Spec 65](../../specification/65-terse-plan-syntax.md).

Slices: design [PR #791](https://github.com/tya5/chrona/pull/791) (`c4c0bc72`); S0 [PR #796](https://github.com/tya5/chrona/pull/796) (`ab530bb7`); S1 [PR #809](https://github.com/tya5/chrona/pull/809) (`dc38c62d`); S2 [PR #811](https://github.com/tya5/chrona/pull/811) (`7d0392e8`); S3 with [#792](https://github.com/tya5/chrona/issues/792) [PR #826](https://github.com/tya5/chrona/pull/826) (`09fa4628`; work record [PR #818](https://github.com/tya5/chrona/pull/818)). Slice 4 (teaching) needed no further change, see row 5. Successors and found defects: [#822](https://github.com/tya5/chrona/issues/822) (deadline mark and terse clause), [#810](https://github.com/tya5/chrona/issues/810) (backward-pass `TemporalError`), [#789](https://github.com/tya5/chrona/issues/789) (determinism), [#780](https://github.com/tya5/chrona/issues/780) (`validate` and cycles).

## Literal issue acceptance

### Issue #788

- Source: [Issue #788](https://github.com/tya5/chrona/issues/788)
- Observed: 2026-10-02

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | An author can state a gate that follows a task without writing its date | met | `schedule: {mode: scheduled-point}` ([PR #809](https://github.com/tya5/chrona/pull/809); schema `scheduledPoint`, Spec 04 section 20.4); [`test_scheduled_point.py`](../../../tests/unit/chrona/scheduling/test_scheduled_point.py) `test_g1_gate_behind_a_duration_task_and_its_fixed_twin`; the twin render test [`test_scheduled_point_render_twin.py`](../../../tests/integration/test_scheduled_point_render_twin.py); in the terse syntax `gate after X +2wd` ([PR #811](https://github.com/tya5/chrona/pull/811), Spec 65). | — |
| 2 | ... or the scheduler's rejection tells them the date to write | met | `E_FIXED_TARGET_VIOLATION` names the earliest feasible date and the forcing relation, with a machine-readable `details` object ([PR #796](https://github.com/tya5/chrona/pull/796); [`test_fixed_target_details.py`](../../../tests/unit/chrona/scheduling/test_fixed_target_details.py), Spec 04 section 20.1). | — |
| 3 | covered by a test with a fixed-point gate behind a duration task | met | [`test_fixed_target_details.py`](../../../tests/unit/chrona/scheduling/test_fixed_target_details.py) `test_gate_behind_a_duration_task_reports_the_date_to_write` (fixed-point gate, duration task) and `test_g1_...` above. | — |
| 4 | (Decide 1) Add a derived point to the Project model: computed from its dependencies (earliest date after its predecessors, with an optional not-earlier-than bound), no stored date; a schema change in place (Spec 56 section 3.2), a scheduler change, and a Scene/View consequence | met | The mode, the floor `constraints.at.min` and a cap `at.max` shipped in place in `timeline/v0.7` with one recorded schema-equivalence delta ([PR #809](https://github.com/tya5/chrona/pull/809)); scheduler and attachment support ([`test_scheduled_point.py`](../../../tests/unit/chrona/scheduling/test_scheduled_point.py), [`test_attachments.py`](../../../tests/unit/chrona/core/test_attachments.py)); the Scene/View consequence is none by construction: a derived gate and its fixed twin render byte-identical SVG and equal Scene (row 1 render test). The as-of and Actual handling of a gate that slips: an Actual never moves a planned date (Spec 04 sections 17 and 20.4), and a slipped promise is the `W_DEADLINE` warning ([PR #826](https://github.com/tya5/chrona/pull/826), [#792](https://github.com/tya5/chrona/issues/792)). | — |
| 5 | (Decide 2) Improve what the existing model reports: `E_FIXED_TARGET_VIOLATION` names the earliest feasible date and the relation that forces it | met | As row 2: [PR #796](https://github.com/tya5/chrona/pull/796), [`test_fixed_target_details.py`](../../../tests/unit/chrona/scheduling/test_fixed_target_details.py). | — |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

The owner's rule is complete: a gate may be derived (`scheduled-point`) and the scheduler's rejection of a fixed guess teaches the date. Layering held: Core and scheduler own the date, presentation reads placements only (twin test), the terse compiler maps and never computes a date. The pair "derived gate plus promise" is: `at.min` floor, `at.max` hard cap (`E_CONTRADICTORY_BOUNDS` with `details`), `deadline` soft warning (`W_DEADLINE`). Slice 4: `docs/guides/cli-reference.md` is generated from argparse flags (no prose to extend), the skill statements that became stale were fixed in slices 2 and 3, and no public example or tutorial change was chosen (lead decision L8); nothing remains for #788.

Disclosures:

- **The #148 go/no-go re-run with three fresh agents** on a plan that needs a derived gate (the plan's slice 2 proof) was not run; it belongs on #148, not to this issue's acceptance.
- **Found, not fixed:** [#810](https://github.com/tya5/chrona/issues/810) (`schedule()` raises `TemporalError` from the backward pass on some plans that mix calendar-day and working-day lags, without a derived point) and [#789](https://github.com/tya5/chrona/issues/789) (hash-seed-dependent `totalFloat` order); the property tests schedule with the analysis pass stubbed for the first. Both are open and outside this issue's rows.
- **`chrona validate` passes a dependency cycle through derived gates** like any other cycle ([#780](https://github.com/tya5/chrona/issues/780)); `schedule` finds it.
- **Terse and View gaps for `deadline`** are [#822](https://github.com/tya5/chrona/issues/822).
- No committed Project or example changed, so no public rendered artifact changed in any slice.

Exact review-bearing-main three-OS CI and newest-Python materializer run must pass before closing #788; record that run in the issue closing comment.

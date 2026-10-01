<!-- chrona:literal-acceptance/v1 -->

# Issue #810 — backward pass and mixed calendar and working-day lags acceptance review

Source: [Issue #810](https://github.com/tya5/chrona/issues/810), observed 2026-10-02 (body plus one comment, mine, the claim and decision record; last updated 2026-10-02). The issue has no checkbox list; its "Needs" paragraph is its acceptance and the table copies it literally, one row per item. Work record: [issue-810-789-scheduler-analysis-work-record-2026-10-02.md](../../planning/active/issue-810-789-scheduler-analysis-work-record-2026-10-02.md).

Slices: docs [PR #835](https://github.com/tya5/chrona/pull/835) (`15a7e218`); implementation [PR #836](https://github.com/tya5/chrona/pull/836) (`d66835ff`).

## Literal issue acceptance

### Issue #810

- Source: [Issue #810](https://github.com/tya5/chrona/issues/810)
- Observed: 2026-10-02

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A minimal reproduction as a failing test. | met | [`test_backward_pass_lag_calendars.py`](../../../tests/unit/chrona/scheduling/test_backward_pass_lag_calendars.py): a fixed point on a Friday feeds a calendar-day `2d` span that ends on a Sunday, which feeds a `5d` span through `1wd` on a six-day calendar (raised `TemporalError("Latest placement precedes earliest placement")`), and a `1wd` span before a gate fixed on a Sunday (reported float 1, correct 0). Both were in the first commit of PR #836 and failed on `main` before the fix. | — |
| 2 | A root-cause analysis (forward and backward passes disagree on lag calendar semantics?). | met | [Work record](../../planning/active/issue-810-789-scheduler-analysis-work-record-2026-10-02.md) sections 1 and 4: the backward pass inverted a lag with `retreat`, which is the inverse of a working-day `advance` only when the endpoint is a working day of the lag's calendar (`advance` counts days strictly after its start, so a whole non-working run advances to one date). The forward pass was right; the backward pass disagreed with it for any source endpoint that is not a working day (calendar-day span end, point, other calendar), and the same cause overstated the float of a working-day span before a non-working target. Fixed by `core/temporal.latest_start_for` (greatest date whose forward `advance` does not pass the target), used for the relation hop and the span start; Spec 57 states the rule. Decisions D1 to D4 recorded on the issue with options and the way back. | — |
| 3 | Design-first handling per AGENTS.md. | met | The [work record](../../planning/active/issue-810-789-scheduler-analysis-work-record-2026-10-02.md) (baseline, literal acceptance, decisions, design, architecture review, implementation plan) was published and merged as [PR #835](https://github.com/tya5/chrona/pull/835) before any product code, with the claim and decisions on the issue. The code PR #836 followed it, Spec 57 and Spec 04 were updated in the same PR, and the record's progress section carries the sweep, the mutation check and the corrections. | — |
| 4 | Removal of the stub in the #788 property tests. | met | `mock.patch.object(scheduler, "_analyze_criticality", ...)` and its import are gone from [`test_scheduled_point_properties.py`](../../../tests/unit/chrona/scheduling/test_scheduled_point_properties.py); a test asserts every generated plan gets a real analysis with non-negative float, and mutating the scheduler to skip the pass is killed by it. All of I1 to I4 pass on the real pass. The #788 plan's note (section 11, item 4) now says so. | — |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

The fix is one pure function in Core temporal arithmetic and three call sites in the scheduler's backward pass; the forward pass, `advance`, `retreat` and every placement are untouched. Import direction is unchanged (`tools/check_import_direction.py`).

Behaviour-preserving evidence: a sweep over all 52 runs (every tracked Project, every Project scenario, every compilable terse fixture) compared placements, diagnostics and the whole analysis before and after. No placement, diagnostic or verdict changed and no run raised before or after. `analysis` changed in 8 Projects, each an instance of the two symptoms and verified by hand (work record section 6): HALCYON-1 `shipment` float 5 to 4 (the old latest start would push `campaign` past its own latest start), the same effect upstream in the baseline snapshot, latest dates that move later on a non-working date with unchanged float (Orion `respin-a1`, derived-gates `floor`), and YAML-hazard `off` float 31 to 30. The `schedule-halcyon-ok` characterization golden changed in exactly that one number. `regenerate_public_examples.py --check` found no derived byte change, and no derived-sync bot commit followed the merge.

Disclosures:

- The committed corpus never raised, so the user-visible change is a corrected float for one HALCYON-1 object (and its copies), not a new success.
- `latest_placements` (not serialized by any adapter) now holds the true latest date rather than the earlier conservative one wherever a latest endpoint falls on a non-working date.
- The `_calendar_distance` guard stays as an internal invariant check (decision D4); a property over 400 generated plans proves it no longer fires.

Exact review-bearing-main three-OS CI and newest-Python materializer run must pass before closing #810; record that run in the issue closing comment.

<!-- chrona:literal-acceptance/v1 -->

# Issue 1936 — comparison controls acceptance review

Controls source: [a78948b41](https://github.com/tya5/chrona/commit/a78948b4120a6dadb1be88e36d263568dd23c9cb).
Authority: [current design/architecture/implementation plan](https://github.com/tya5/chrona/issues/1936#issuecomment-6353606699), Specs06/07/24/33.
[Reviewer disposition](https://github.com/tya5/chrona/issues/1936#issuecomment-6354568694): land controls after PR1938; the reviewer then adopts them in02 and obtains owner comparison. This is a partial functional review, not release acceptance; keep issue1936 open.

## Literal issue acceptance

### Issue #1936

- Source: [Issue #1936](https://github.com/tya5/chrona/issues/1936), including [row6](https://github.com/tya5/chrona/issues/1936#issuecomment-6353600428)
- Observed: 2026-10-23

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
|1|a note can be declared as a numbered marker at its anchor plus a numbered entry in a declared list slot, with no leader; numbering follows a declared order (anchor time, or View order). Synthetic test; then 02 adopts it.|not met|Synthetic Scene/SVG View-order indices, numbered list entries, no box/leader, explicit suppression and opaque candidate identity: [tests](../../../tests/integration/test_annotation_terminal_list_index_1936.py). Actual02 adoption remains reviewer-owned.|—|
|2|a View can draw baseline ghosts with no labels of their own (the current plan keeps its label).|met|`comparison.baselineLabels:none` retains the paired Snapshot mark and primary label; actual SVG/Scene [controls](../../../tests/integration/test_issue_1936_rendered_controls.py). Default, explicit/removed-only/forecast ownership: [model controls](../../../tests/unit/chrona/presentation/test_issue_1936_controls.py).|—|
|3|a group header can be placed as a band label inside the timeline surface (as the mock's SPACECRAFT BUS), with no table column.|met|Actual timeline-owned SVG header/band, zero-width table, source owner growth and explicit vertical incompatibility: [tests](../../../tests/integration/test_timeline_group_header_1936.py). Default table geometry retained.|—|
|4|a Theme token sets the gap between a mark and its side label, and relation arrowheads keep clear of label boxes.|not met|Shared full-footprint `timeline.mark.labelGap`; inherited/explicit stroke, profile admission, clipping and actual SVG [gap controls](../../../tests/integration/test_member_label_painted_gap_1936.py), [folded controls](../../../tests/integration/test_folded_forecast_painted_gap_1936.py), [ink controls](../../../tests/unit/chrona/presentation/layout/test_mark_painted_ink_1936.py). Ordinary-candidate head clearance remains coordinated with devB1908: [concrete witness](https://github.com/tya5/chrona/pull/1940#issuecomment-6354050438).|—|
|5|a delta label/column can declare that a zero delta is omitted.|met|Actual SVG/Scene signed cells, ordinary/attached delta components, nonzero/missing/default controls: [tests](../../../tests/integration/test_issue_1936_rendered_controls.py). Opt-in key-row extent/pitch filters zero and measures all remaining deltas; default probe preserved: [tests](../../../tests/unit/chrona/presentation/layout/test_key_row_delta_omission.py). Facts remain unchanged.|—|
|6|the slot-output check exempts a slot that the spec collapses, using the same rule; the known-failure entry is removed and the check passes on 02.|not met|Synthetic serialized Scene proves the exact Spec24 collapsed-table exemption: [tests](../../../tests/integration/test_timeline_group_header_1936.py). Actual approved02 still has six table-owned headers and a positive-width table; its known-failure entry is already absent. Recheck actual02 after reviewer adoption.|—|

## Programme-level criteria (optional)

No separate programme criterion replaces the pending literal rows above.

## Architecture and release disposition

View selects names, zero display and header ownership; Theme selects paint/gap. Layout resolves completed geometry through neutral effective-paint and profile-admission inputs, sharing path stroke arithmetic with terminal bounds. Scene projects the same paint contract; no Scene/profile object enters Layout. Exact round-capped lines retain segment obstacles. Required identities, raw facts and frozen schema definitions remain intact; no Project/corpus data or generated outputs were authored. Correct inherited-outline bounds may change lane packing and require public delta disclosure, not a legacy-bound fallback.

Focused controls: earlier278 passed; full schema-equivalence L1/L2/L3 and source-only guards passed. Final adjacent lane/host/forecast/paint regression batch102 passed. Earlier consolidated150-case batch had148 passes and two fixture errors; both corrected and targeted11 passed. These overlapping runs are not a full-suite claim. PR public-materializer/SVG-Scene audit, final-head CI and the exact review-containing-main three-OS pytest/conformance/wheel-smoke release are pending. No issue closure is authorized by this record.

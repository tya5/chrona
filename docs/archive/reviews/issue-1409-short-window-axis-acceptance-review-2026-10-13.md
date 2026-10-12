<!-- chrona:literal-acceptance/v1 -->

# Issue1409 — short-window default axis

Implementation [PR1442](https://github.com/tya5/chrona/pull/1442) is merged on
`1dbad8798335cb25f3208f9356cbac3eea84da58`;
[head CI38275814117](https://github.com/tya5/chrona/actions/runs/38275814117) passed
on `e2b80df9`. [Work record](https://github.com/tya5/chrona/issues/1409#issuecomment-6106476083).
Closed after [exact-main release38279118426](https://github.com/tya5/chrona/actions/runs/38279118426)
passed on review-containing `9573049a` (Windows/macOS/Ubuntu, MCP and
newest-Python public reproduction). Archive follows closure; no new behavior.

## Literal issue acceptance

### Issue #1409

- Source: [Issue1409](https://github.com/tya5/chrona/issues/1409)
- Observed: 2026-10-13

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A test over windows from one day to ten years with the default preset: every window shows at least two labels in its finest tier, and no labels intersect. | met | Nine Scene/SVG windows1/2/7/14/31/90/365/1826/3652 days plus the existing exact-ten-year regression. Truthful one-day singleton is explicitly approved by [reviewer6125010480](https://github.com/tya5/chrona/issues/1409#issuecomment-6125010480); longer cases have at least two. No intersections, exact temporal endpoints. | — |
| 2 | Explicitly declared tiers without opt-in are byte-identical. | met | All46 local public materializers match full published Scene/SVG bytes; [current-head CI artifact](https://github.com/tya5/chrona/actions/runs/38275814117/artifacts/11758877688) independently reports zero changed derived paths. Fixed-unit selection and other preset resources are untouched. | — |
| 3 | Do not edit `examples/**`. | met | [Exact implementation diff](https://github.com/tya5/chrona/pull/1442/files): default bundled View, Spec39 and two tests only. | — |

## Programme-level criteria (optional)

No additional closing criterion. The one-day rendered label is `JAN 4, 2027`
for exactly `[2027-01-04, 2027-01-05)`, not a month label or widened window.

## Verification and architecture

Own-venv focused tests:61 passed4.73s (default-window, packaged-policy,
regular-cadence/mapping-order, presentation-axis and placement controls).
Public materializer batch:46/46 complete Scene/SVG byte identity.
Only the default's auto forms add existing day/week forms. View admission,
Theme typography, Layout density/geometry and Scene/adapter ownership stay
unchanged. No new schema, padding, fabricated labels or compatibility branch.

Commands: `python -m pytest -q` on the default-window and packaged-policy tests,
plus `test_axis_regular_cadence.py`, `test_presentation_axis.py` and
`test_axis_placement.py`; `python -m tools.routing_performance_evidence
--output-dir <empty-dir> --jobs 4`.
The PR CI passed all three pytest shards, conformance, MCP floor and
newest-Python materializer reproduction. Exact-main release of the commit
publishing this review remains mandatory; local/PR passes do not replace it.

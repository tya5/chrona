<!-- chrona:literal-acceptance/v1 -->

# Issue #1626 — grouped import acceptance

Candidate: [PR #1650](https://github.com/tya5/chrona/pull/1650),
head `8e660a04f914a30dab70e5086884d112ce5f7c4c`, based on ready main `cf1218655`.
Final-head PR checks and exact review-containing release remain pending.

## Literal issue acceptance

### Issue #1626

- Source: [Issue #1626](https://github.com/tya5/chrona/issues/1626), with [reviewer replacement of row2](https://github.com/tya5/chrona/issues/1626#issuecomment-6230791458)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Trace posted; synthetic twins for grouped import with and without a responsible role. | met | [Trace and architecture](https://github.com/tya5/chrona/issues/1626#issuecomment-6229468273); [neutral integration twins](https://github.com/tya5/chrona/blob/9bbe5f202/tests/integration/test_role_group_summary_order.py) cover declaration/explicit/time order, bound-role omission/count, selection, direct-field/none controls and role-normalization idempotence. | — |
| 2 | on the trial CSV, target-b without `--role` shows Design, Build and Release in CSV order. With `--role responsible=owner`, target-b and sunday show no group-summary bars in an Unassigned lane, and the diagnostic is present. Viewed as PNG. | met | Exact [trial3 inputs](https://github.com/tya5/chrona/tree/dbbce45e60392b7b0be788f841fe2673f4830944/trial3), project-only README renders: target-b no-role shows Design→Build→Release; target-b/sunday with-role omit the3 summary bars and emit `I_VIEW_FIELD_GROUP_SUMMARIES_OMITTED` with count3. All3 PNGs viewed; no declared grouping-none design changed. | — |
| 3 | Public SVG/Scene changes listed with counts. | met | [Official PR snapshot](https://github.com/tya5/chrona/actions/runs/39020052383/artifacts/12095624016): all 50 SVG and 50 Scene pairs byte-identical; each slide has zero routes, labels or primitives changed/added/removed and zero new diagnostics. Only the diagnostic inventory report changes. | — |

## Programme-level criteria (optional)

Current-base focused checks:49 role/normalization/forecast/occurrence and16
diagnostic inventory tests passed. Require final-head PR checks, then three-OS full
pytest/conformance/wheel and public reproduction on exact main containing this
review. Keep issue1626 open until those gates pass.

The Sunday role/direct-field matrix and quality-bound guards pass (34 focused
tests). Role grouping verifies three omitted summaries; direct-field grouping
retains the original required-barrier and quality-fallback witness. Both retain
all route-completeness, suppression, crossing and expansion-safety checks.

## Architecture conclusion

Role-origin normalization preserves the declared grouping contract; projection
owns declaration order and selected summary omission. Typed info carries a count,
not Layout policy. No nested grouping mechanism, schema migration, preset copy,
source mutation or Scene/adapter geometry rule. Nested Project-group plus lane
presentation is only a successor candidate to mention when closing, not this scope.

Trial-only side effect: corrected no-role target-b order introduces one
`W_SCENE_RELATION_THROUGH_MARK` (Kickoff→AuthAPI across UX Research). Both baseline
and candidate already have two overlap resolutions; their count does not increase.
Spec50 §1427 permits non-host mark relaxation under declared `relax`; Scene
observes the crossing and the existing render warning adapter translates the
perceptibility error into a warning. This diagnosed routing tradeoff does not
change grouping acceptance or justify project-specific core/preset patches.

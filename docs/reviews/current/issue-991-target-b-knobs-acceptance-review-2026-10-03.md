<!-- chrona:literal-acceptance/v1 -->

# Issue #991: the knobs approved target B still needs, acceptance review

Source: [Issue #991](https://github.com/tya5/chrona/issues/991), re-fetched 2026-10-03 (body unchanged since filing; 13 comments: the owner's items 10 to 14, this work's claim, decisions and status blocks, the reviewer's items 15 to 17, and the owner's decision on item 17). The three rows below are the three literal acceptance bullets of the body; the seventeen items they refer to are listed with their evidence under the programme-level section. Work record: [issue-991-target-b-knobs-2026-10-03.md](../planning/active/issue-991-target-b-knobs-2026-10-03.md) (baseline, design plan, design with the owner-level decisions, architecture review, implementation plan); living contracts [Specification 06](../../specification/06-view-model.md), [07](../../specification/07-style-and-theme.md), [34](../../specification/34-color-scheme-authoring.md) and [39](../../specification/39-axis-and-observation-clarity.md).

The reviewer owns `examples/halcyon-1` 21-target-b and its adoption of each knob; this work changed none of its files except the one edit the reviewer permitted (the `missing-actual` fill binding, in PR #1025).

## Literal issue acceptance

### Issue #991

- Source: [Issue #991](https://github.com/tya5/chrona/issues/991)
- Observed: 2026-10-03

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Each item lands as a general knob or fix with synthetic tests, or is declined with a reason. | narrowed | Items 1 to 14, 16 and 17 landed as general knobs or fixes, each with synthetic tests and a mutation check (every PR is linked in the programme-level table below; design [PR #999](https://github.com/tya5/chrona/pull/999), record [issue-991-target-b-knobs-2026-10-03.md](../planning/active/issue-991-target-b-knobs-2026-10-03.md)). Narrowed parts: item 2 shows the calendar **id** for `{calendar}` because a Project calendar has no title; item 3's in-progress mark is not available with lane rows (`E_REVIEW_MISSING_ACTUAL_SCOPE_LANES`); item 15 (the relation entry side) is a router candidate-order change that moves every slide and is not done here. | [#1026](https://github.com/tya5/chrona/issues/1026) calendar title for `{calendar}`; [#1027](https://github.com/tya5/chrona/issues/1027) in-progress hatch with lane rows; [#1030](https://github.com/tya5/chrona/issues/1030) relation entry side (searched: relation entry, candidate order, ports, `connector_egress_candidates`; no duplicate) |
| 2 | Item 3's legend crash is fixed regardless. | met | [PR #997](https://github.com/tya5/chrona/pull/997) (`ca9cb595`): a Theme role bound to a catalogue pattern (`hatch-wide`) crashed the legend swatch with `E_THEME_TOKEN_TYPE` because Layout patterned only the chart's marks; the key is now patterned with its mark's role. Failing synthetic test first ([`test_legend_catalog_pattern.py`](../../../tests/integration/test_legend_catalog_pattern.py), crash before, pass after, key shares the mark's geometry and paint, plain without a pattern), mutation checked, no corpus output changed. | none |
| 3 | After each landing, the reviewer updates the #987 YAML. Do not change the target-B files yourself; they are on the reviewer's branch `reviewer/987-target-b`. | narrowed | Not changed by this work except one reviewer-permitted edit inside [PR #1025](https://github.com/tya5/chrona/pull/1025): only the `missing-actual` fill binding of the target-B Theme (accent to surface, so the in-progress bar is a blue hatch on white and passes the blocking mark gate; `tools.presentation_contrast` 0 errors), recorded on #991. The adoption itself is the reviewer's step, not this work's: [PR #1016](https://github.com/tya5/chrona/pull/1016) adopted gate paint, note inset, header role, line colour and exception paint; the in-progress rule, per-state delta text, kind colour header and `{subjectId}`, `ghost-when-changed` and the foot chip are for the reviewer to adopt. | [#987](https://github.com/tya5/chrona/issues/987) (the reviewer's target-B assembly) |

## Programme-level criteria (optional)

The seventeen items of #991 and their landing (each PR carries synthetic tests, a mutation check, and spec text; rendered evidence was read against the mock `02-programme-board.png` where the knob is visual, as recorded in each PR description):

| Item | Knob | PR (commit) | Evidence read |
| --- | --- | --- | --- |
| 1 | `comparison.baselineMarks: ghost` (ghosts with grouped automatic rows) | [#1000](https://github.com/tya5/chrona/pull/1000) (`ad430b21`) | Controller Z `baseline-ghosts` |
| 2 | View `heading` title and subtitle templates | [#1003](https://github.com/tya5/chrona/pull/1003) (`9a99b9f7`) | Controller Z `heading` |
| 3 | `comparison.missingActualScope: in-progress`; legend crash | [#1007](https://github.com/tya5/chrona/pull/1007) (`155204a7`), [#997](https://github.com/tya5/chrona/pull/997) | Controller Z `in-progress` |
| 4 | as-of marker `placement: foot`, date forms `day-month`, `day-month-year` | [#1006](https://github.com/tya5/chrona/pull/1006) (`ae8264e9`) | Controller Z `as-of-foot` |
| 5 | `ordering.by: source` | [#1008](https://github.com/tya5/chrona/pull/1008) (`d2ae8d95`) | row-order render test |
| 6 | Theme role `gate` | [#1011](https://github.com/tya5/chrona/pull/1011) (`5e2e6519`) | Controller Z `gate-paint` |
| 7, 11 | `annotationKinds.colorAlso`, `{subjectId}` | [#1021](https://github.com/tya5/chrona/pull/1021) (`dfdb849f`), [#1023](https://github.com/tya5/chrona/pull/1023) (`59906330`) | synthetic renders |
| 8 | Theme role `calendar-exception` | [#1019](https://github.com/tya5/chrona/pull/1019) (`615d490a`) | Controller Z `calendar-exception` |
| 9 | table column `missingBy` | [#1020](https://github.com/tya5/chrona/pull/1020) (`203b0060`) | synthetic render |
| 10 | `contentInsetEm` for every container outline | [#1012](https://github.com/tya5/chrona/pull/1012) (`7ddd09f9`) | synthetic render |
| 12 | legend swatch centring (bug) | [#1009](https://github.com/tya5/chrona/pull/1009) (`841a20e6`) | 21-target-b legend |
| 13 | Theme text role `tableColumnLabel` | [#1015](https://github.com/tya5/chrona/pull/1015) (`7906fc2c`) | Controller Z `table-header` |
| 14 | optional Scheme colour `rule` | [#1018](https://github.com/tya5/chrona/pull/1018) (`2018e710`, merged by the lead) | Controller Z `line-colour` |
| 15 | relation entry side | not done | successor [#1030](https://github.com/tya5/chrona/issues/1030) |
| 16 | `baselineMarks: ghost-when-changed` | [#1029](https://github.com/tya5/chrona/pull/1029) (`c3d8183c`) | synthetic projection tests |
| 17 | the owner's in-progress rule | [#1025](https://github.com/tya5/chrona/pull/1025) (`094c4df9`), [#1028](https://github.com/tya5/chrona/pull/1028) (`d80055ce`) | synthetic cases and 21-target-b |

## Architecture and release conclusion

Every knob is optional and absent means today's output byte for byte (public materializers unchanged until a slide declares it); the layers are respected: View and Theme and Scheme declare, the content layer composes text and rows, Layout owns geometry (ghost tracks, chip candidates, legend centring, header metrics, insets), Scene applies completed paint (`gate`, kind colour, `calendar-exception`, header role), adapters decide nothing. Schema additions follow Specification 56 section 3.2 (in place, `python -m tools.schema_equivalence --base-rev origin/main` passing per slice, stale S0 entries pruned by the next schema PR). No gate was weakened: new roles are classified (`gate` mark, `calendar-exception` decoration), the header contrast gate now judges a kind colour used as ink against the note box, and the blocking mark gate caught and fixed the in-progress hatch ink.

Disclosures:

- **`{calendar}` is the calendar id**, not a name (#1026).
- **The in-progress hatch is not available with lane rows**, whose expected-mark inventory is closed (#1027); the bundles use lane rows.
- **Item 15 is not done** (#1030); every slide with relations would change and the policy needs its own design.
- **Rendered output was read** from Chrome and resvg renders of the evidence slides; the muted subtitle colour and the chip fill are Theme content for the reviewer.
- **Adoption of the knobs in 21-target-b** is the reviewer's (#987).

Exact review-bearing-main three-OS CI must pass before closing #991; that run is recorded in the closing comment.

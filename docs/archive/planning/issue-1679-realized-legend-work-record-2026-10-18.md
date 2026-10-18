# Issue 1679: realized legend work record (2026-10-18)

Status: accepted and closed. PR1692 merged `6de463805`; final6cf CI39093575302
and review-containing exact-main `4e30fbc3f` release39094741641 passed all
required gates. All four literal rows are met; the final artifact preserves
the reviewed50-slide counts and PNG evidence. Board454 remains read-only.

## Baseline and literal acceptance

Implementation base `82c1e96b6` includes S2/PR1687 and #1680/PR1689.
Integrate the latest ready `main` before the product push; dev B owns
#1682/#1681/#1683 and its current landing window. Trial inputs are public
`reviewer/trial-5-inputs` at `9fa6062de`; no previous private files are assumed.

1. A synthetic project with actuals, rendered with executive-light: every distinct realized mark paint has exactly one legend key, and the actual and progress keys use the realized paints.
2. When an encoding replaces the planned paint on every planned mark, no base planned swatch remains; the encoding's entries stand in its place. A mixed case (some planned marks unencoded) keeps the base key.
3. target-b without snapshot or actual has no baseline, actual or in-progress keys and no empty Δ column.
4. A count table of the public example changes, and the PNGs checked.

## Design plan and selected design

Use cases: explain the actual range and progress ink; remove unused base/encoded
keys; omit unavailable comparison columns; avoid redundant same-colour keys or
canvas growth caused only by conservative candidates. No open owner question.

Normative ownership: [Spec28](../../specification/28-review-detail-profile.md)
owns grouping, representative geometry, wording and final extent;
[Spec60 §4](../../specification/60-declared-colour-scales.md) owns encoded/base
coverage; [Spec61](../../specification/61-progress-fill-marks.md) owns Progress;
[Spec06](../../specification/06-view-model.md) owns source absence/wording;
[Spec49](../../specification/49-semantic-presentation-contract.md) owns the shared
paint witness. Do not duplicate those contracts here.

Compatibility impact: unavailable columns, unused/mismatching keys and redundant
Progress keys disappear; split Actual groups use their own qualifier instead of
repeating the base. Whole glyph figures remain intact. No source YAML, project
data, schema version or semantic registry role changes. First premeasured group
representation stays stable when final visibility changes its member witnesses.

## Whole-architecture review

- Model/Theme carry pure completed ink and neutral renderer capabilities;
  colour grouping is separate from exact rendering paint. No Scene imports in
  Layout or duplicate paint resolver. Scene retains bounds-dependent effects.
- Layout measures potential candidates, closes visibility from completed
  placements, selects one final entry set and replaces candidate-only legend
  extent for canvas completion. Chart rows/routes/annotations are not retried.
  Typed Progress host identities prevent comparing unrelated colours.
- View normalizes source absence before table measurement; supplied-empty is
  not absent, Snapshot alone cannot supply ordinary Actual delta, and required
  input errors remain errors. No B-owned field/default/label-packing changes.
- Scene projects exact scalar or completed sibling Symbol paints. SVG/PNG and
  strict contrast see the same whole figure. No contrast exemption or palette
  substitution. Finite circle/rule-pair keys remain intentional projections.
- Independent Luna identity/canvas audits confirmed the owner seams. Regression
  risks are representation/footprint stability, fill-versus-border identity,
  typed host matching, caption restoration and accidental non-legend movement.

## Implementation plan

One coherent product PR1692, not partial main landings. Published initial plan
`492c8512e` preceded I1–I4; corrective plans above precede current edits.

| Slice | Owned files/boundary | Tests and publication gate |
| --- | --- | --- |
| I1 paint parity | `model/theme_paint.py`, neutral capabilities, Scene paint bridge | Shared channel/override/gradient resolution; Style/Actual/finite-shape tests, Scene ownership. Exact full paints retained. |
| I2 source normalization | `review/v05_content.py`, source-presence closure | Absent versus supplied-empty Actual, Snapshot-only, forecast/scenario columns; one column list drives both cells and measurement. |
| I3 final legend | `legend_ink.py`, `legend_candidates.py`, `realized_legend.py`, `surface_legend.py`, composer | Premeasured groups, typed occurrences, final encoded/base filtering; complete composite miniatures and exact part handoff. |
| R1 reviewed coalescing | `model/legend_paint.py`, candidate/final filter | Shared fill-first palette with stroke-only fallback; same-colour geometry variants merge, qualifier-only splits, host-specific redundant Progress omitted; representative/footprint stability. |
| R2 final extent | `surface_composer.py` | Restore final legend slot against original allocation and captions; synthetic excess candidate growth leaves final canvas and non-legend geometry unchanged. |
| I4 release | Synthetic integration tests and acceptance review | Focused tests, ownership/conformance; official snapshot all50 count table, targeted Sunday/Gates/glyph and native Trial PNGs. Exact-head CI, then exact-main three-OS/full release containing review. |

Root owns integration/publication; up to three Luna agents own disjoint bounded
code/tests or read-only review. Source YAML and canonical generated output stay
untouched. A discovered contract gap returns to design before product edits.

## Evidence and remaining gate

CI follow-up architecture correction: role-selected legend icons previously
bound the single `legend:<role>` label, while realized labels have distinct
hashed IDs. Spec28 now selects every final label of a requested role through
an explicit Layout mapping; absent roles still fail closed. No Scene fields,
schema, source-YAML changes or inferred ID aliases. Extend I3: `SurfaceLegendBatch`
closes role→label targets; composer hands them to `place_text_visuals`, which
expands only semantic legend selectors (exact-ID selectors remain singular).
Synthetic tests cover one/multiple Actual groups, wrong/absent roles and
preserved hashed IDs. The all-encoded Planned inventory fixture must instead
use a surviving role. This keeps View intent, Layout identity/geometry and
Scene projection responsibilities separate; publish before code resumes.

CI39090738185 disposition: snapshot/reproduction/MCP pass. Conformance fails15
legend-checker findings; the three pytest shards fail12/12/10 tests. All are
triaged: canonical source IDs versus physical lane aliases; a dataclass-only
test-double assumption; shared-paint errors not mapped at the use-case boundary;
unused-key/source-presence/phase fixtures; stale private generated mirrors; and
role-based visual binding. No independent failure is being ignored.

I4 checker alignment compares complete ordered milestone part paints, exact
Progress hosts and fill-first redundancy, and respects optional legend regions.
Wrong ink, missing nonredundant keys, corrupt/missing parts, unrelated hosts and
relation bounds retain negative tests. Official50-scene reevaluation has zero
findings. Controller regression tests retain independent `tests/fixtures/`
inputs, as required by the retired-example guard. Their affected private golden
SVG/Scene outputs are refreshed for the approved legend change; public canonical
outputs remain CI-owned. No source-YAML or public generated-repo edits.
These corrections preserve the published contracts; role-visual fanout is the
explicit pre-code design correction above. Current-head CI must verify all fixes.
Focused evidence (overlapping batches, not summed): lane/forecast/source identity79;
paint/legend/checker/ownership67; phase/date/terminal30; legend visual/extent8;
fixture materializer tests7 plus relation-label1. Native role visuals cover
one and three hashed Actual groups; absent Planned still fails closed. Composer
remains orchestration-only (394 lines); import and literal-review gates pass.

- Official66f snapshot [CI39092648869](https://github.com/tya5/chrona/actions/runs/39092648869):
  all50 SVG/Scene pairs are byte-identical to the counted a7fc snapshot. Coverage
  and contrast reports are unchanged; diagnostics inventory differs only in
  source locations. Conformance, reproduction and MCP pass. Pytest shard1 finds
  the retired-example-reference regression; shards2/3 pass. Correction
  `e77fff742` restores fixture ownership without weakening the guard; its guard
  and affected tests pass11. Final6cf CI39093575302 subsequently passed.
- Sunday has seven keys and no legend overflow; Gates five and no viewport
  warning. Reviewer accepts true contrast findings; no corpus repair is planned.
- [Literal acceptance review](../reviews/issue-1679-realized-legend-acceptance-review-2026-10-18.md)
  contains official counts/PNG evidence and final CI/release links. Closure and
  exact-main acceptance precede this archival publication.

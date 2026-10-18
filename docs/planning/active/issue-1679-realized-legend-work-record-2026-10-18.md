# Issue 1679: realized legend work record (2026-10-18)

Status: implementing reviewer [6244640261](https://github.com/tya5/chrona/pull/1692#issuecomment-6244640261).
Selected correction/design review `ccf2f99df`, implementation amendment
`4a497c1df`, and fill/border clarification `69c6a33f3` are published before
their product edits. PR1692 still needs the coherent correction push, official
snapshot counts and exact-main release. No release acceptance is claimed.

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

CI39090738185's snapshot/reproduction/MCP pass, but conformance's
`legend-key-scene-evidence` fails15 findings: the checker compares each
multipart milestone key part against the first source part, and still requires
a Progress key for same-host ink. Extend I4 in `tools/check_legend_keys.py` and
its unit/integration twins to compare complete figure paint/part witnesses and
the approved fill-first host redundancy rule. Preserve negative mismatched-ink,
missing nonredundant-key and relation-bounds checks; do not exempt public slides.
This is checker conformance to published Specs28/61, not a product-policy change.

- I1/I2 and native encoding/source tests pass; all50 public materializers were
  batched once, then only affected slides rerendered. Preliminary table is
  explicitly not final; replace it from the next official CI snapshot, not
  another full local render batch.
- PR head `1ecf36452` [CI39088644589](https://github.com/tya5/chrona/actions/runs/39088644589)
  failed snapshot generation on flattened glyph-part contrast. Reproduction
  and readiness failed downstream; tests were skipped. Complete composite
  correction `02bcefa7f` passes strict targeted glyph contrast with zero errors.
- Targeted reviewed Gates has five keys and no canvas warning. Sunday has no
  legend overflow; fill-first redundant Progress removal is under verification.
  Reviewer accepts the genuine contrast findings; no corpus repair is planned.
- [Literal acceptance review](../../reviews/current/issue-1679-realized-legend-acceptance-review-2026-10-18.md)
  must receive corrected official counts/PNG evidence and current CI links.
  Confirm every row and exact-main release before deliberate closure/ledger
  update; archive only after closure. Keep board454 read-only.

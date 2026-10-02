# Issue #493: axis secondary label (work record)

Living record for [#493](https://github.com/tya5/chrona/issues/493): baseline, design plan, design, architecture review and implementation plan. Edited in place; Git keeps history. Normative behavior lives in [Specification 39](../../specification/39-axis-and-observation-clarity.md), "Axis secondary labels (#493)".

**Public base:** `339d87d4` on `main`. **Status:** this record (sections 1 to 7) is published (PR #933); the `labelGap` amendment (D6, sections 5.4, 5.7 to 5.8, 6, 7) is a second docs PR; no code is published yet.

## 1. Published baseline

Issue #493 has no comments (body read 2026-10-02; the claim comment is mine). It was filed from #426 acceptance row 10 and is the P4-B item of the axis lane; #492 (ticks, closed by its review) found that two labels in one cell need a View declaration change and a second measured text, and left it open.

Read on `339d87d4`:

1. **One labels tier draws one text per interval.** `layout/surface_axis.py:compose_axis` formats one string per interval (`format_axis_tier_label(interval, form, name_table)`), measures it (`axis_label_fits`, `measure_text_width`), applies the tier `overflow` policy (`thin-with-record` omits a label whose own clipped interval cannot hold it, `W_LAYOUT_AXIS_LABEL_THINNED`; `visible-overflow` places it and records the overflow), and places one `TextPlacement` `axis-label:<tier>:<index>` through `place_text`.
2. **The label declaration is a closed per-unit object.** In `schemas/view-v0.28.schema.yaml` each unit branch of a labels tier declares `label: {form, align, overflow, orientation, nameTable?}` with `additionalProperties: false`; `unit: auto` declares `forms` instead of `form`. There is no place for a second form. `review/v05_content.py:_axis_tier` detaches it into `AxisLabelIntent`; Layout never sees raw View.
3. **Lanes are sized by one text role.** A labels tier's `typographyRole` (admitted names `axis`, `axisMonth`, `axisQuarter`, `axis2`, `axis3`, `scene/capabilities.py`) sizes the lane (`fontSize * lineHeight`, or the declared `laneBlockSize`, #426) and is measured by `metric_for_role`. Colour comes from the tier's ordinal semantic id (`axisLabel`, `axisLabel2`, `axisLabel3`), not from the typography role.
4. **The name tables already give two scripts.** `ja-JP` `short-month` is `3月`, `en-US` `short-month` is `Mar` (Spec 63); a role's `textTransform` makes it `MAR`. A kanji-numeral month (`三月`) is not a table form and is not part of this issue.
5. **Gates read every Text primitive.** `scene/perceptibility.py` reports `E_SCENE_TEXT_INTERSECTION` (two texts overlapping by more than 4 px squared), `E_SCENE_TEXT_OCCLUDED` and `I_SCENE_PAINT_CONTRAST` for every Text primitive of a scene; `surface_quality.py` requires a hosted axis label's host to be an axis band shape. Axis label roles carry no contrast class (`semantic_registry`), so no axis label has a contrast floor today.
6. **Targets** (read as pictures and READMEs, `docs/research/presentation/`): Title Card shows a compressed Mincho `三月` with a small `MAR` (README row "Axis tiers": "bilingual month tier"); Tenth Frame shows "boxed axis cells, each with a small corner box holding the month number" (README: "no sub-box in a cell"). The mapping of each to a placement (section 4) is inferred from those descriptions, not from text that names a placement.
7. **Fonts.** The optional `chrona-fonts-noto-cjk` package supplies Noto Sans JP metrics; `examples/controller-z-ja` already measures `ja-JP` axis labels with it. A CJK case can therefore be measured and viewed.

**Unverified at baseline:** whether two `TextPlacement`s in the `timeline-axis`/`labels` collision domain trip a Layout overlap check when they do not overlap (checked by the first test), and how `unit: auto` selection would weigh a secondary (not needed, see decision D5).

## 2. Literal acceptance (copied from the issue)

1. A labels tier can declare a secondary form rendered smaller in the same cell, both measured and fitted, and one committed slide shows it.

## 3. Dependencies and neighbours

- #426 (lanes, `typographyRole`), #432 (name tables), #482 (thinning) are closed and supply the mechanisms reused here. #492 (ticks) touched the grid branch of the same function; this work touches only the `labels` branch.
- Other agents work on #584 (annotation kinds), #822 (deadline mark), #812 (MCP read tools): no file of theirs is touched. Shared files are the View schema (`view-v0.28`), `conformance/schema-equivalence/expected-deltas-v0.1.yaml`, `scene/capabilities.py` and Specification 39; every PR rebases on `origin/main` before publication.
- #453 (gap map) and #718 (presets and parts) are read only. No preset or catalogue Theme is edited: adopting a secondary label in a preset is a preset-owner decision.

## 4. Design plan

### Use cases

| Id | Use case | Target |
| --- | --- | --- |
| U1 | A month cell reads `3月` and, smaller beneath it, `MAR` | Title Card |
| U2 | A month cell reads `MAR` with its number `03` smaller, on the same line, after it | Tenth Frame (inline stand-in for the corner box) |
| U3 | A cell too narrow for the secondary still shows its main label, and the omission is recorded | all |
| U4 | A View that declares no secondary renders byte-identically | every committed example |

### Open decisions (closed in section 5)

- **D1 where the secondary is declared.** A `secondary` object on the tier's `label`; or a second labels tier that shares the first tier's lane; or a Theme declaration.
- **D2 the secondary's role.** Own typography role (size, weight, family, transform) and own colour role; or own typography role with the tier's colour.
- **D3 placements.** Which of stacked, inline, corner, and what each measures.
- **D4 narrow cell behaviour.** Omission versus ellipsis; per cell versus per tier; a static lane that cannot hold the stack.
- **D5 scope.** `unit: auto`, rotated orientation, repeated secondaries.
- **D6 the gap between the two texts.** A Theme knob, a measured quantity, or both.

### Responsibility and architecture review questions

- Does the declaration (content: which second form of the same interval, in which name table) belong in the View while size and colour stay Theme-owned, and Layout stays the only owner of measurement and placement?
- Is the secondary measured by the same function and the same font metrics path as the primary, with no width constant anywhere?
- Do omission and the static lane failure use the existing axis diagnostic families?
- Do the existing perceptibility gates cover the secondary without a new gate, and is that proven by a test that fails when the secondary overlaps or is occluded?
- Does the addition follow Specification 56 section 3.2 and pass `python -m tools.schema_equivalence --base-rev origin/main`?
- Byte identity: no `secondary` means the same code path and the same bytes for all committed slides.

### Acceptance evidence planned

Synthetic tests only, no `examples/` input: stacked and inline geometry from measured widths, each omission reason, the thinned-primary case, alignment `start` and `center`, a declared lane that cannot hold the stack, an unknown or absent Theme role, schema rejections, default byte identity, perceptibility on the produced scene. Mutation checks on the new tests. The S0 gate result in the schema PR. Rendered images read in full, including a CJK case measured with Noto Sans JP. The literal acceptance review per section 2.

## 5. Design

### 5.1 Declaration (D1, D5)

An optional `secondary` object on a labels tier's `label` (View v0.28, in place, no version bump, Spec 56 section 3.2: omission is today's behavior).

```yaml
- unit: month
  every: 1
  role: labels
  typographyRole: axisMonth
  label:
    form: short-month
    nameTable: ja-JP
    align: center
    overflow: thin-with-record
    orientation: horizontal
    secondary:
      form: short-month          # a form valid for the same unit
      nameTable: en-US           # optional; defaults as the primary's does
      typographyRole: axisSecondary
      placement: stacked         # stacked | inline
```

`form`, `typographyRole` and `placement` are required (no hidden default for what the reader sees). `form` is constrained per unit by the same form definitions the primary uses. The secondary is declared on the tier's `label`, not in a second tier: a second tier owns its own lane (#426), cannot share a cell, and would thin independently of its primary. Allowed only on a fixed `unit` (the `auto` branch gives no `secondary` property) and only with `orientation: horizontal` (conditional in the schema). One secondary per cell.

### 5.2 Content and typed intent

`review/v05_content.py:_axis_tier` detaches it into `AxisLabelIntent.secondary: AxisSecondaryIntent | None` (form, name table id, typography role, placement); the name table id is resolved and validated as the primary's is. Layout reads only this intent.

### 5.3 Role (D2)

The secondary has **its own typography role** (`typographyRole`, a Theme text role: size, weight, family, spacing, transform; admitted by adding `axisSecondary` to the axis typography role contract in `scene/capabilities.py`; any admitted axis role may be named) and **shares its tier's colour**: its text carries the tier's ordinal semantic id (`axisLabel`, `axisLabel2`, `axisLabel3`), so every Theme that colours the tier already colours the secondary and no preset needs an edit. A distinct colour is an additive successor (a registered semantic id and Scene role, one declaration in each Theme that uses it); it is not built because no target text requires it. A Theme without the named role fails with the existing Theme token error, never a fallback.

### 5.4 Geometry (D3, D6)

Let `Hp` and `Hs` be the line boxes (`fontSize * lineHeight`) of the tier's role and the secondary's role.

- **gap:** the secondary's typography role may declare `labelGap`, a ratio of that role's own font size (the shape of `labelInset`, #426). Absent, the gap is **0 for `stacked`** and **one measured space of the primary's role for `inline`** (`measure_text_width(" ")` with the primary treatment: a measured quantity, not a width constant). A declared gap is the distance between the two line boxes (`stacked`) or between the two texts (`inline`).
- **stacked:** the secondary sits on the line below the primary, aligned like the primary (`start` at the label inset, `center` centred, each line on its own). The pair occupies `Hp + gap + Hs`. In a declared lane the pair is centred in the lane; otherwise the tier's lane grows to that block (plus the tolerance the lane already carries).
- **inline:** the secondary follows the primary on the primary's baseline, separated by the gap. The pair is aligned as one unit. The line occupies the shared-baseline extent of the two texts (`max(Hp, Hs)` for same-proportion fonts).
- **corner** (Tenth Frame's sub-box) is not built: a box needs a Theme-owned background and padding and is a different mechanism. Additive successor: another `placement` value.

All widths come from `measure_text_width` with the font metrics of each text's own role, the function the primary uses.

### 5.5 Narrow cells and the static lane (D4)

Per interval whose primary is placed:

| Condition | Result |
| --- | --- |
| primary placed and fits, and the secondary fits (stacked: its width at most the cell's available inline size; inline: primary + gap + secondary at most that size) | both drawn |
| the secondary does not fit | the secondary is omitted; the primary is drawn as without a secondary; `W_LAYOUT_AXIS_SECONDARY_OMITTED:<primary id>:does-not-fit` and a suppressed `PlacementDecision` for `axis-label-secondary:<tier>:<index>` |
| the primary itself overflows (`visible-overflow` policy) | the secondary is omitted with reason `primary-does-not-fit`, same diagnostic form |
| the primary was thinned | nothing of the cell is drawn; no secondary diagnostic (the thinning record covers the cell) |

There is **no ellipsis rung**: a truncated `Ma…` or `3…` misreads, and axis labels have no ellipsis today (the rules are omission with a record). The secondary never changes the primary's fit, thinning or `unit: auto` selection, which are computed from the primary alone, so adding a secondary cannot thin a label that fit without it.

**Per tier, not per cell,** the block geometry is fixed: in `stacked` the primary keeps its upper-line position in a cell whose secondary is omitted, so baselines stay aligned along the axis. If the block (stacked: `Hp + gap + Hs`; inline: the shared-baseline extent) cannot lie inside the tier's declared lane, or inside the axis slot for an undeclared lane, Layout raises `E_PRESENTATION_AXIS_OVERFLOW` (detail `secondary-lane:<tier>`), the family the band lanes and the #492 tick length use. This is a Theme/slot mismatch the author must fix, not a per-cell condition to drop silently.

### 5.6 Output and gates

Each drawn secondary is one `TextPlacement` `axis-label-secondary:<tier>:<index>` in the same `timeline-axis` collision domain, hosted by the same axis band rule as the primary, and projected by Scene like any axis label (no Scene or adapter change). The existing gates therefore apply to it with no new gate: text intersection with its primary, occlusion by a later opaque rect, and the paint contrast observation. The typed `AxisIntervalOutcome` gains `secondary_label`, `secondary_disposition` (`placed` or `omitted`) and `secondary_reason`, validated by `surface_quality`. `W_LAYOUT_AXIS_FORM_EQUIVALENT` also fires for a non-canonical secondary form, with the secondary's id.

### 5.7 Schema and migration

Two optional properties are added in place. (1) `view-v0.28`: the optional property (a view-local `$defs/axisSecondaryLabel` for the shared object, referenced by each unit branch with the unit's form definition beside it), recorded with one L1 expected-delta entry. (2) `theme-v0.11` and `theme-v0.13`: the optional role property `labelGap` (a named number token, the shape of `labelInset`), admitted with the other axis measurement properties. `python -m tools.schema_equivalence --base-rev origin/main` runs for both and its result goes in the PR. No version bump, no corpus migration; the default path is unchanged.

### 5.8 Owner decisions (also posted on #493)

| Id | Options | Choice | Why | How to reverse |
| --- | --- | --- | --- | --- |
| D1 | A `label.secondary` object; B second tier sharing a lane; C Theme declaration | A | the secondary belongs to its cell (shares its disposition, form unit and fit); B needs a lane-sharing rule and thins independently; C puts content in the Theme | none needed; B could be added as a different tier role without removing A |
| D2 | own typography role and colour role; own typography role, tier colour | own typography role, tier colour | works with every Theme without an edit; size is what the issue asks for | add a semantic id and Scene role later; a Theme that declares it would take precedence |
| D3 | stacked; inline; corner | stacked and inline | each is a pure measured placement; corner needs a box (Theme background) | add `corner` to the `placement` enum |
| D4 | omit; ellipsis; per tier or per cell | omit per cell with record; static lane failure errors | no misleading fragment; matches thinning; baselines stay aligned | add `ellipsis` as another rung only with a reading rule |
| D5 | support `auto` and rotated | fixed unit and horizontal only | `auto` selection would have to weigh the secondary; rotation has no agreed stacking | widen the schema branches |
| D6 | knob; measured space; both | a measured space by default plus an optional Theme role property `labelGap` (also a vertical gap when stacked) | no width constant, yet an author can open the pair when one space reads as a single token (a rendered probe of `Jan` + `01` did) | drop `labelGap` from the admission and schema; the default stays valid |

## 6. Architecture review

| Boundary | Result |
| --- | --- |
| View | One optional object, in place; it names content (which second form, which table, which Theme text role, where in the cell), not coordinates or colours. `unit: auto` and rotated labels are excluded by schema. |
| Theme | One optional role property `labelGap` added in place to v0.11 and v0.13 (Spec 56 section 3.2, the shape of `labelInset`); `axisSecondary` is admitted as an axis typography role; colour reuses the tier's ordinal role. A missing role fails with the existing token error. |
| Content | Detaches the declaration into a typed intent; formats nothing. |
| Layout | Owns formatting through the name table, measurement, fit, placement and the omission and lane rules inside the existing `labels` branch; the primary path is untouched when no secondary is declared. |
| Scene and adapters | Unchanged: one more Text primitive per drawn secondary. |
| Gates | Existing perceptibility and hosting checks cover the new text; the test suite proves it by overlap and occlusion cases. No contrast floor exists for axis labels today; adding one is outside this issue and unchanged for the primary. |
| Neighbours | #492 grid branch, #426 lanes and separators, #482 thinning and `unit: auto` selection act on the primary and are unchanged. #583 (group headers) uses a different template mechanism and file. #584, #822, #812 files are untouched. |

**Findings:** (1) the secondary must never influence the primary's fit, or a Theme change could silently thin labels; decided and tested. (2) A per-cell vertical shift would misalign baselines; decided per tier. (3) Sharing the colour keeps presets untouched but cannot colour the secondary differently; recorded as the D2 successor, not filed. **Risk:** a Theme whose lane is too short for a stack gets `E_PRESENTATION_AXIS_OVERFLOW`; intended and diagnosable.

## 7. Implementation plan

Four publications: this docs PR; I493-1; I493-2; the acceptance review. Each code PR is `Refs #493`.

**I493-1: declaration, content, Layout, tests.**
- `schemas/view-v0.28.schema.yaml` (the `axisSecondaryLabel` def, `secondary` on each unit branch, the horizontal condition) and `conformance/schema-equivalence/expected-deltas-v0.1.yaml` (one L1 entry); `schemas/theme-v0.11.schema.yaml` and `schemas/theme-v0.13.schema.yaml` (`labelGap`, beside `labelInset`). Run the S0 gate and record it.
- `model/surface_content.py` (`AxisSecondaryIntent`, `AxisLabelIntent.secondary`), `review/v05_content.py` (`_axis_tier`).
- `scene/capabilities.py`: add `axisSecondary` to the axis typography role contract and `labelGap` to the axis measurement properties.
- `layout/surface_quality.py` (`AxisIntervalOutcome` secondary fields and their validation), `layout/surface_axis.py` (the secondary placement, the omission and lane rules, both lane cursors), `usecases/diagnostic_messages.py` (the new warning text).
- Tests `tests/unit/chrona/presentation/scene/test_axis_secondary.py` built on `_axis_tiers_scene`, plus a schema test: stacked geometry from measured widths (line positions, `Hp + gap + Hs`), inline geometry with the measured space and with a declared `labelGap`, the stacked gap, `start` and `center` alignment, each omission reason and its diagnostic and decision, thinned primary draws neither, the secondary never changes the primary's fit or thinning, a lane that cannot hold the stack raises, a role absent from the Theme fails, perceptibility has no `E_SCENE_TEXT_INTERSECTION` or `E_SCENE_TEXT_OCCLUDED` on the output and does report one for a forced overlap, the default path is primitive-for-primitive identical to the pre-change output, schema accepts and rejects (auto, rotated, missing required, wrong form for the unit). **Mutation check** on measurement, the fit comparison, the omission, the lane guard and the alignment.
- Evidence: `tools/regenerate_public_examples.py --check` shows every existing slide byte-identical; conformance; the focused and presentation pytest suites.
- Boundary: no example, preset, Theme schema, Scene or adapter file.

**I493-2: committed slides.** `examples/controller-z-ja` `axis-secondary` (view, Theme with an `axisSecondary` role, context, manifest entry): `3月` with `MAR` stacked, measured with Noto Sans JP. A Latin `controller-z` `axis-secondary-inline` slide (`MAR` with `03`) is added when it shows the inline rule without editing any existing file. SVG and Scene are bot-generated (a PR never authors declared evidence); the author renders them locally and reads the images, including one cell narrowed to the omission rung. Public-evidence counts in `tests/unit/tools/test_derived_evidence.py`, `test_presentation_coverage.py` and `tests/acceptance/output/test_public_geometry_regressions.py` move with the new slides.

**Acceptance review:** `docs/reviews/current/issue-493-axis-secondary-label-acceptance-review-<date>.md` with the `chrona:literal-acceptance/v1` marker and one row per literal criterion, checked by `tools/check_issue_acceptance_reviews.py`, then the three-OS run on the exact commit that publishes it.

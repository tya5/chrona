# Issue #1111: legend swatch sizing knobs (work record)

Living record for [#1111](https://github.com/tya5/chrona/issues/1111): a swatch-to-label gap apart from the entry gap, a declarable size for area (background) swatches, and a point swatch size. Baseline, design plan, design, architecture review and implementation plan are published together before code. Edited in place. Found by the reviewer's tuning PR #1061 against `docs/research/presentation/halcyon-1-target-design-2026-09-21/board/02-programme-board.png` (22 x 12 swatch, 6 px to the label, 26 px to the next entry). Siblings: [#427 swatches](issue-427-legend-swatches-design-plan-2026-09-26.md), #497 (content sizing), #1009 (centring), #1062 (legend colour, [record](issue-1062-text-roles-2026-10-04.md)).

**Public base:** `d93c3687`. **Status:** design published, no code yet. **Scope rule (owner):** core knobs and their own evidence only; the reviewer's `examples/halcyon-1/*target-b*` files are not edited (PR #1061, #987 adopt the knobs).

## 1. Published baseline

Read on `d93c3687` (`layout/surface_legend.py`):

1. `legend_item_gap(slot.gap, legend_size)` is the one distance between a swatch and its label **and** between entries (absent slot `gap`: half the legacy swatch, `0.4 x legend size`). It is used by `legend_source_input` (measurement: each run is swatch extent plus gap, runs `run_gap` apart) and by `place_legend` (inline: `x += width + gap + label + gap`; block: label at swatch end plus gap, rows `gap` apart).
2. `swatch_extent(role)` returns a `(inline, block, bucket)`: `point` for `milestone` (side = planned `markHeight` x mark block), `mark` for roles with mark geometry (inline = `legend-swatch.swatchInlineSize` or the legacy square side, block = role geometry x mark block), `line` for as-of, dependency and deadline (inline likewise, block = label line), and `legacy` for everything else: the square `0.8 x legend size`. Area roles (`calendar-closed`, `calendar-exception`, any other role) are therefore a fixed square and ignore `swatchInlineSize`.
3. `swatchInlineSize` is an optional `legend-swatch` Theme role property (a named number token, `theme-v0.11` and `v0.13`); the committed `halcyon-1/themes/print.yaml` declares it, so area swatches in that Theme must **not** start following it, or its output changes.
4. Measurement and drawing both call `swatch_extent`, so a size change reflows the legend slot with no second path (#497). Row height is the larger of the label line and the swatch (#1009 centring), already generic.
5. Contrast: legend labels are ground text (#884, #980, #1062); swatch paint is the entry role's own paint. Geometry knobs touch neither.

Unverified (checked in the slice): corpus bytes; the perceptibility gate on a larger area swatch in the evidence slide.

## 2. Literal acceptance (copied from the issue)

| # | Criterion (synthetic fixtures, published Scene) |
| --- | --- |
| A1 | With `swatchGap` g and slot gap G, every label starts g after its swatch's end, and every next swatch starts G after the previous label's end. |
| A2 | An area-role swatch has the declared inline and block size. |
| A3 | A point swatch has the declared size. |
| A4 | Absent declarations give byte-identical output. |
| A5 | Target B: 22 x 12 swatches, 6 px swatch gap and 26 px entry gap, as in the mock. |

A5 is the reviewer's adoption step (scope rule): recorded as narrowed with successor #987 and PR #1061; the knobs are shown on a Controller Z slide.

## 3. Design (decisions; reverse = remove the optional property and its consumer branch)

Home: the `legend-swatch` Theme role (it already owns swatch size; the swatch gap is a presentation size, not Layout Profile structure, so no Layout Profile schema change and no edit to bundled Profiles). Three optional named number tokens, all absolute px like `swatchInlineSize`:

- **D1 `swatchGap`** (>= 0): distance from a swatch's end to its label. The slot `gap` is only the distance between entries (inline: label end to next swatch; block: between rows). Absent: the swatch-label distance is the slot gap, exactly today's single gap. Measurement (`inline_advance`, the ellipsis floor and the item minimum) and drawing read the one helper.
- **D2 `swatchBlockSize`** (> 0): turns the area (`legacy` bucket) swatch into a rectangle: inline = `swatchInlineSize` if declared, else the legacy side; block = `swatchBlockSize`. **Opt-in on `swatchBlockSize`** (owner-level choice): the issue says area swatches should "take `swatchInlineSize`", but a Theme that already declares `swatchInlineSize` (`print.yaml`) would change output; declaring the new `swatchBlockSize` is the opt-in, so absent declarations stay byte identical and no corpus regeneration is needed. Alternative rejected: change the default for every Theme declaring `swatchInlineSize` (behaviour change: corpus regeneration and grouped image review). Reverse: apply `swatchInlineSize` to the area bucket unconditionally.
- **D3 `pointSwatchSize`** (> 0): side of the point (milestone) swatch. Absent: the on-chart gate size, as today.
- **Validation.** A value that is not a number, a size <= 0 or a gap < 0 is `E_THEME_TOKEN_TYPE` at `/body/roles/legend-swatch/<property>`. The role is admitted by the capability table (`legend-swatch`, consumer "Layout legend swatch size") with the three new properties.
- **Adapters.** Typst, TikZ, SVG (and PNG, PDF from SVG) serialise completed Scene primitives: the swatch is a Rect or Symbol with Layout-completed bounds and the label a Text at its completed position. No adapter reads the knobs; the evidence checks the bounds in the Scene and the coordinates in the Typst and TikZ output.
- **Contrast and perceptibility.** Unchanged: labels stay ground text; a larger area swatch only changes its extent. The evidence slide runs the contrast and perceptibility gates.

**Schema (Spec 56 section 3.2; S0).** `theme-v0.11` and `theme-v0.13`: three optional properties in `roles.additionalProperties.properties` (additive, no version bump; precedent #1066 `symbolHeight`). `python -m tools.schema_equivalence --base-rev origin/main` is run and recorded in the code PR. Specification 07 (Theme roles) and 49 (`legendEntry`) are updated; migration impact: none.

## 4. Architecture review

View untouched; Theme declares sizes; Layout owns swatch and label geometry (one `swatch_extent` and one gap helper used by measurement and drawing); Scene and adapters unchanged. Defaults byte identical (corpus `--check`). The opt-in coupling in D2 is the one deliberate asymmetry and is documented. Failure: invalid token is the existing Theme token error. Risk: a swatch taller than the label line grows the row (#1009 centring already handles it).

## 5. Implementation plan

| # | Slice | Files | Tests | Evidence |
| --- | --- | --- | --- | --- |
| 0 | This record (docs PR) | this file | conformance | none |
| 1 | Three tokens, one gap helper, area and point sizes (one code PR) | `layout/surface_legend.py`, `model/theme_tokens.py` (validated readers), `scene/capabilities.py`, `theme-v0.11`, `theme-v0.13`, Specifications 07 and 49 | synthetic integration for A1 to A4 (inline and block direction, ellipsize floor, validation, defaults byte identity); mutation check | Controller Z slide `legend-swatches` (own Theme through YAML); Typst and TikZ read |
| 2 | Acceptance review | `docs/reviews/current/issue-1111-*` | `tools/check_issue_acceptance_reviews.py` | exact-commit three-OS run |

Each PR: `Refs #1111`, failing test first, rendered image read, `git diff --stat origin/main` limited to the slice, merge lock rules. Owner-level decisions are also commented on #1111.

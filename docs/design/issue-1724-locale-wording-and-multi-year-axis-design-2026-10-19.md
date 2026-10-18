# Issue 1724: locale wording, multi-year dates and the default axis (design)

**Status:** Design for review, 2026-10-19. Base: `origin/main` 41465471c.
Evidence: branch `reviewer/trial-7-inputs`, `trial-7/`. Issue: #1724 (all PRs use `Refs #1724`).
This note is published before code because item 4 extends public schemas (View,
Review Detail Profile, a new bundled resource). Items 1, 2, 3, 5 and 6 are
fast-path items (one PR each, plan in the issue); they are described here only
so the whole issue has one ordering. Normative text goes into the living
specifications named per item, not into this note.

## 0. Baseline and constraints

- Default render (no `--preset`) uses `presets/default.yaml`, which resolves to
  the bundle `editorial-readable-default` (view, theme, layout) with the
  `editorial` detail profile (`src/chrona/resources/presets/`).
- Existing wording mechanism (Spec 06 section 9.3): the View `wording.legend`
  and `wording.summary` maps (schema `common-v0.1#/$defs/viewWording`) override a
  profile label. `legend_wording` reaches Layout through
  `SurfaceContentInput.legend_wording` (`presentation/model/surface_content.py`,
  consumed by `layout/legend_candidates.py` and `review/profile_connections.py`).
  Dev A (#1727) adds the key `critical-edge` with English default
  `Critical dependency`, read in `review/v05_content.py` from
  `wording.legend.critical-edge`. Item 4 must keep exactly that precedence.
- Axis name tables (Spec 63) are the precedent for a bundled, closed,
  locale-selected table (`resources/axis-name-tables-v0.1.yaml`, schema
  `axis-name-tables-v0.1.schema.yaml`, `presentation/model/axis_names.py`).
- Presets (`src/chrona/resources/presets/**`, `designs/**/layout.yaml`) and
  `examples/**` are reviewer-owned. This design does not edit them; where a
  preset must change it is listed in section 9 and requested on the issue.

## 1. Observed 1: multi-year plans drop the year in the table

- **Root cause.** `presentation/model/surface_content.py`: `_format_date_range`
  decides the year per row (`start.year == end.year` omits it);
  `display_value` also calls `_format_compact_date(..., include_year=False)` for
  single dates and inclusive ranges. No code knows the visible range crosses a
  year, so two rows in different years both read `27 Apr - 03 May`.
- **Rule.** A table date drops its year only when the whole visible range stays
  inside one calendar year. Otherwise every `dateRange` cell shows the year on
  both ends. Visible range = resolved View window (not the selected-item span
  when a window is declared). A range crossing a year inside one cell keeps the
  current both-years form.
- **Design.** `normalize_v05_table_content` (`review/v05_content.py`) resolves
  the window's first and last visible date once and passes `years_visible: bool`
  (true when the two dates are in different years) to `display_value`, which
  forces `include_year=True`. Compact form stays `DD Mon YYYY` / `YYYY年M月D日`.
- **Spec.** Spec 24 (the `dateRange` column paragraph near line 44): add the
  visible-range year rule.
- **Public schema change:** none.
- **Tests.** Synthetic two-year plan: every cell has a year; one-year plan:
  byte-identical to today; window narrower than the plan (one visible year) keeps
  no year; ja-JP form. Unit tests beside the existing display-value tests.
- **Side effects.** Only slides whose resolved window spans two calendar years
  change; for each, `dateRange` cells gain years, and a content-width `Plan`
  column grows (plot width shrinks, so labels/routes can move). The PR body
  carries the per-slide count table (cells changed, plot-width delta, new
  diagnostics). The exact slide list is produced by
  `regenerate_public_examples.py --check`; I expect a small minority of the 50.

## 2. Observed 2: default axis has only a week tier

- **Root cause.** In `bundles/editorial-readable-default/view.yaml` the `year`
  (band) and `quarter` (grid-major) tiers carry no labels tier. The only
  `role: labels` tier is `unit: auto`, which resolves to weeks for a short
  window, so nothing names a month or a year. (Engine behaviour is by design:
  Spec 39, a band tier draws no text of its own.)
- **Rule.** When the finest labelled tier is `week` or `day`, the default axis
  also labels `month`, and the year at its boundaries.
- **Chosen design (no schema change).** Fix in the preset, using supported
  grammar: add two fixed-unit `labels` tiers (`year` with form `year`, `month`
  with form `short-month`), in front of the auto tier, each with
  `overflow: thin-with-record`. Spec 39 already lets several labels tiers occupy
  consecutive lanes (`axisLabel`, `axisLabel2`, `axisLabel3`). Alternative
  (engine-side synthesis of a coarser tier when the auto tier lands on week) is
  rejected: it hides a tier the View did not declare and breaks "Layout reads
  what the View declares".
- **Needs the reviewer.** This is an edit to preset YAML (`view.yaml` of
  `editorial-readable-default`, and, if wanted, `editorial`, `executive-light`
  which share the same auto tier). Request on the issue; I do not edit it. The
  work is code-free apart from the theme typography role (`axisMonth` exists in
  the designs; `editorial-readable-default/theme.yaml` must declare it).
- **Spec.** Spec 39: one sentence recording the default-axis contract; the
  bundled-default sentence already in Spec 39 (#1409) is the place.
- **Public schema change:** none.
- **Tests.** Preset-level: render a 4-month synthetic window; assert Scene has
  one month and one year label cell (by tier index) in addition to weeks.
- **Side effects.** Every slide rendered with the default preset family changes
  (extra axis lane, plot block size shrinks by one or two lane heights, vertical
  re-flow of rows). Disclosed as the count table: axis primitives added, plot
  height delta. Slides using a `designs/*` layout already have month tiers and do
  not change.

## 3. Observed 3: the year boundary leaves a hole

- **Root cause (partly verified, partly hypothesis).**
  `presentation/axis_intervals.py` does not split a week at the year boundary:
  the week owning Dec 28 is one natural ISO bucket (`2026-W53`), clipped only by
  the window edge. The blank column therefore comes from
  `layout/surface_axis.py` (about lines 395-440, 1029): label fit is local, but
  `thinning_schedule` (`layout/axis.py`) picks one phase-zero stride for the whole
  tier, so a single clipped/narrow edge cell whose label does not fit forces
  stride > 1 or drops the label (`W_LAYOUT_AXIS_LABEL_THINNED`), and the cell
  keeps its slot. The 95 px empty band is a reserved lane (typographic
  `laneBlockSize`) for a tier none of whose labels were placed. The implementer
  must first reproduce with a synthetic window ending in the first week of a new
  year, and confirm which of the two applies, before coding.
- **Rule (proposed).** A cell that is clipped by the window edge and whose label
  does not fit is not part of the cadence decision: it is recorded as omitted
  (`W_LAYOUT_AXIS_LABEL_THINNED:...:clipped-edge`), and the other labels keep the
  stride computed from the unclipped cells. A labels lane is reserved only when
  at least one of its tier's labels is placed.
- **Spec.** Spec 39 (regular-cadence paragraph): the clipped-edge exemption and
  the lane-reservation rule.
- **Public schema change:** none (a new reason string in an existing warning's
  payload; documented in `docs/diagnostics/inventory.md`).
- **Tests.** Synthetic windows ending on Dec 28-31 / Jan 1-4; assert no blank
  column between retained labels, lane absent when empty.
- **Side effects.** Slides whose last or first week is a clipped, unfitting cell
  (labels re-appear, or a lane disappears: plot height grows). Count table.

## 4. Observed 4: built-in wording per locale (public schema change)

This is the item that needs a design first.

### 4.1 Where the English literals live

| Text | Literal source |
| --- | --- |
| Table headers `Task`, `Plan` | `tableColumns[].id` of the preset View; header text is the id (`TableColumnContent(column.id, column.id, ...)`, `review/v05_content.py`) |
| `Task` / `Lane`, `Items` | `_default_lane_header`, `_lane_table_content` (`review/v05_content.py`) |
| `TODAY` | preset View `markers[].label` (required string) and designs `markerPresentation.label` |
| Legend `Task duration`, `Actual`, `Milestone`, `Dependency`, `Today`, `Weekend` | `bundles/*/detail.yaml` `legend[].label` (required string); `WEEKEND` upper case is a typography transform |
| `Critical dependency` | `v05_content.py` default (Dev A) |
| `unknown`, `in progress`, `As of` | `display_value` missing table; `_as_of_label` |
| `calendar-closed` role label `Weekend` | the same role also draws public holidays (`calendar_closures`) |

### 4.2 Rule

- One bundled, closed, validated resource `wording-tables-v0.1.yaml`
  (schema `wording-tables-v0.1.schema.yaml`), modelled on the axis name tables:
  a table per supported locale (`en-US`, `ja-JP`), each mapping the same finite
  set of wording keys to text. Adding a locale is a table entry. A test lists the
  keys and fails when any locale lacks one (this is acceptance 2's key list).
- Initial keys: `column.task`, `column.plan`, `column.lane`, `column.items`,
  `marker.today`, `marker.asOf`, `legend.planned` (text `Task duration`),
  `legend.actual`, `legend.milestone`, `legend.dependency`, `legend.asOf`,
  `legend.calendar-closed` (text `Non-working day` / Japanese equivalent, never
  `Weekend`: the role is keyed as a closed day, which covers holidays),
  `legend.critical-edge` (`Critical dependency`), `missing.unknown`,
  `missing.inProgress`.
- **Precedence (lowest to highest), one mechanism:**
  1. table entry for the Render Context locale; if absent the `en-US` entry
     (tables are validated complete, so this is a defence only);
  2. a literal string authored in the profile/preset (unchanged behaviour: an
     authored literal is never translated);
  3. View `wording.keys[<key>]` (new, generic override, see below);
  4. View `wording.legend.<role>` / `wording.summary.<id>` (existing, most
     specific; wins over `wording.keys["legend.<role>"]` if both are given).
  Dev A's `critical-edge` therefore stays valid: `wording.legend.critical-edge`
  is level 4, and the default is the table entry `legend.critical-edge`
  (English `Critical dependency`) instead of an inline literal. No project-specific
  text, no second locale mechanism.
- Selection: the Render Context locale only (same as axis tables default), plus
  the existing explicit `nameTable` on axis tiers is untouched.

### 4.3 Public schema changes (all additive or loosening, Spec 56 section 3.2)

1. `common-v0.1#/$defs/wordingRef`: `{wording: <key>}` where `<key>` is the
   closed key enum from the table schema.
2. View `tableColumns[].header`: optional; a string or `wordingRef`. When absent
   the header stays the `id` (byte-identical). Rows/`hierarchyColumn` still refer
   to `id`, so ids need not change.
3. View `markers[].label`: string or `wordingRef` (was string).
4. Review Detail Profile `legend[].label`: string or `wordingRef` (was string).
5. `viewWording`: new `keys: {<wording key>: <text>}`; unknown key is
   `E_VIEW_WORDING_UNKNOWN` (existing code) at its pointer.
6. New resource `wording-tables-v0.1` (+ schema), bundled in the wheel.
No version bump is proposed: every change loosens or adds an optional property
(Spec 56 section 3.2). `python -m tools.schema_equivalence --base-rev origin/main`
runs in the PR and its result is recorded there. If the reviewer reads (3) and
(4) as breaking for external validators, the fall-back is View v0.29 with the
same content; this is open question Q2.

### 4.4 Code

- New `presentation/model/wording_tables.py` (loader/validator, like
  `axis_names.py`); a resolver `resolve_wording(key, locale, overrides)`.
- `review/v05_content.py`: column headers, markers, lane headers and
  `critical-edge` call the resolver. `surface_content.display_value` gets the
  resolved `missing` words as arguments (it stays pure; no locale lookup inside).
- `review/profile_connections.py`: legend label ref -> resolver before the
  existing override pass.
- Uppercase rendering of keys such as `WEEKEND` stays a typography transform and
  is not part of the table.
- Spec: 06 section 9.3 (precedence, `keys`), 24 (table header), 45 (legend
  vocabulary and the closed-day role), 63 (sibling resource pointer).

### 4.5 Presets (reviewer-owned, request via the issue)

Presets keep working unchanged (literals are authored text, level 2) but stay
English under `ja-JP` until they reference keys. The reviewer must change, in
the bundles used by the 50 slides: `tableColumns` `header: {wording: column.task}`
and `column.plan`; `markers.label: {wording: marker.today}`; `detail.yaml`
legend entries to `{wording: legend.*}`; and `designs/*/layout.yaml`
`markerPresentation.label` if a layout wording reference is wanted (not
included here). This is the only way to make acceptance 2 pass for the default
preset and for yuya. Code PR (4a) can land before the preset PR; acceptance 2 is
only met after the preset PR.

### 4.6 Tests and side effects

- A test enumerates the keys and asserts every locale has all of them, no key
  maps to another locale's text, and each preset/profile reference names a known
  key. A render test with `--locale ja-JP` on the default and yuya scenes asserts
  no `Task`, `Plan`, `TODAY`, `WEEKEND`, `Actual`, `Milestone`, `Dependency`
  English text is left in table/legend/marker primitives.
- Authored override test: all four precedence levels.
- Side effects: en-US output is byte-identical with the same table text
  (the table texts are exactly the current literals except
  `legend.calendar-closed`, which changes `Weekend` to `Non-working day` only
  when a preset references the key, i.e. in the preset PR). Under ja-JP the
  affected slides are only those rendered with `--locale ja-JP`; the 50 public
  slides are en-US, so none change in 4a. The preset PR changes the legend
  text of every slide that draws a closed-day legend entry (count table needed).

## 5. Observed 5: one glyph diagnostic per glyph

- **Root cause.** `presentation/model/font_metrics.py` adds one
  `FontGlyphSubstitution` per `(family, fallback, weight, codepoint, value)`;
  `usecases/render_review.py` (line ~520) wraps each into a `FontGlyphFallback`
  info diagnostic (`presentation/model/info_diagnostics.py`), and
  `usecases/warning_ledger.py` / `diagnostic_messages.py` do the same for the
  warning form `W_FONT_GLYPH_SUBSTITUTED`. 354 distinct codepoints give 354 entries.
- **Rule.** One entry per `(requestedFamily, fallbackFamily, weight, script)`
  with `count` (distinct codepoints) and the first sample (`codepoint`, `text`).
  Script is the Unicode block name (stdlib `unicodedata` is not sufficient; use
  a small closed range table for Hiragana, Katakana, CJK Unified Ideographs,
  fullwidth forms, other).
- **Design.** Aggregate in one place, `render_review.py` before building the
  info diagnostics and in `warning_ledger.py` for the warning form, through one
  shared function so both stay equivalent. Payload keeps `requestedFamily`,
  `fallbackFamily`, `weight`, `codepoint` (first sample) and `text`, and gains
  `script` and `count`.
- **Spec.** Spec 30 (line ~112): the substitution rule becomes grouped.
  `docs/diagnostics/inventory.md`: payload.
- **Public schema change:** none to a JSON schema (the Scene diagnostic is a
  string whose JSON payload gains two keys; CLI JSON warnings gain `script` and
  `count`). This is a changed public diagnostic payload, so the PR discloses
  it in the count table.
- **Tests.** Synthetic Japanese text with many distinct kana/kanji: at most one
  entry per script block with the right count; existing
  `tests/integration/test_automatic_cjk_fonts.py` and
  `tests/cli/test_cli.py` expectations updated.
- **Side effects.** Slides with substituted glyphs lose per-glyph diagnostics
  (count of removed entries per slide); no geometry change.

## 6. Observed 6: a guide for `--locale` and wording

- **Design.** New section "Localizing a render" in
  `docs/guides/render-review-yaml-layout.md` (it already mentions the locale
  line 22): `--locale en-US|ja-JP`, which text each locale changes (dates, axis
  names, built-in wording keys, with the key list from 4.2), how to override
  (`wording.legend`, `wording.keys`), and a runnable example. The example is a
  `chrona` fenced plan or `sh` fence the existing doc checks execute
  (`tools/check_documented_commands.py`, `tests/unit/tools/`), so acceptance 4
  is enforced. Also add a one-line `--locale` pointer in `skills/chrona/SKILL.md`
  references if the skill owns authoring guidance (open question Q5).
- **Depends on 4.** The example shows a wording override and the Japanese
  header; it lands after 4a.
- **Public schema change:** none. Side effects: none on slides.

## 7. Proposed PR split (one PR per item; `Refs #1724` only)

| Order | PR | Item | Needs design/schema | Depends on |
| --- | --- | --- | --- | --- |
| 0 | this docs PR | design | - | - |
| 1 | P5 | 5 glyph diagnostic grouping | no (payload) | none |
| 2 | P1 | 1 year in table dates | no | none |
| 3 | P3 | 3 year-boundary hole | no | none (reproduce first) |
| 4 | P4a | 4 wording tables, resolver, schema, spec, tests | yes (this note) | owner acceptance of Q1-Q3 |
| 5 | P4b | 4 preset references (reviewer) and ja-JP acceptance test | preset edit | P4a merged |
| 6 | P2 | 2 default month/year labels (reviewer preset edit) | no schema | reviewer; independent of P4 |
| 7 | P6 | 6 guide with runnable example | no | P4a |

One active item per session: P5, P1, P3 are independent and small; if three
are green and waiting they may go out as one integration PR (AGENTS.md batching).
P4a is the only item whose side effects on the 50 slides are none by design.

## 8. Risks

- P1 changes plot width for default slides spanning two years; check for new
  overflow warnings in the PR table.
- P3's cause is a hypothesis until reproduced; the implementer records the
  reproduction in the issue Status comment before changing code.
- P4a adds an open-ended key surface; the closed enum and the all-locale
  completeness test are the guard.

## 9. Open questions (recommendation recorded; none blocks the work)

| # | Question | Recommendation |
| --- | --- | --- |
| Q1 | Owner: one generic `wording.keys` override plus existing `wording.legend/summary`, or only role-specific maps? | Add `wording.keys` (one mechanism for every built-in key, keeps `legend.*` working and Dev A's `critical-edge`). |
| Q2 | Is loosening `label` to string-or-ref and adding `header` an in-place change, or a View v0.29? | In place (Spec 56 section 3.2: additive/loosening); run `schema_equivalence`; fall back to v0.29 only if the reviewer objects. |
| Q3 | Name and text of the closed-day legend key (`Weekend` is wrong for holidays). | Key `legend.calendar-closed`, en-US `Non-working day`, ja-JP `休業日`; the role id is unchanged. |
| Q4 | Reviewer: edit presets to reference keys (4.5) and add month/year label tiers (section 2)? | Yes, in two reviewer PRs after P4a; code lands first, English output unchanged. |
| Q5 | Should the agent skill (`skills/chrona`) also document `--locale`? | Yes, one line pointing to the guide; no duplicated rule. |
| Q6 | Year rule for a declared narrow window inside a multi-year plan: visible range or plan range? | Visible window (what the reader sees); the plan span is irrelevant. |
| Q7 | Item 3 fix: exempt clipped edge cells from cadence, or merge the clipped cell into its neighbour? | Exempt and record (`clipped-edge`); merging changes cell identity and Spec 39 natural-bucket geometry. |

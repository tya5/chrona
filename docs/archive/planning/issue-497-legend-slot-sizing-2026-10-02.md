# Issue #497: content-sized legend slot and silent ellipsis (work record)

Living record for [#497](https://github.com/tya5/chrona/issues/497): baseline, design plan, design, architecture review, implementation plan and progress. Edited in place; Git keeps history.

**Public base:** `4981db0a` on `main`. **Status:** I497-1 (measure, bound, report, PR #853), I497-2 (the gate, PR #856) and I497-3 (corpus read: no corpus slide still truncates, so no corpus edit; the [acceptance review](../reviews/issue-497-legend-slot-sizing-acceptance-review-2026-10-02.md)) are done. Published before code: design plan (section 4, PR #840), design and architecture review (sections 5 and 6, PR #841), implementation plan (section 7, PR #851).

## 1. Published baseline

Issue #497 has no comments (body amended 2026-09-29: acceptance split into a general rule and corpus evidence). #454 lists it under "layout slot sizing and legend" with #499.

Reproduced on `4981db0a` from the committed Scenes (`examples/halcyon-1/generated/`):

| Slide | `legend` slot inline size | `legend:*` texts ending in an ellipsis |
| --- | ---: | ---: |
| `02-programme-board` | 64.6 px | 8 of 9 |
| `12-glyph-gates` | 64.6 px | 8 of 9 |
| `15-gallery-image-notes` | 64.6 px | 8 of 9 |

No other committed Scene has a truncated `legend:*` text (a scan of every `examples/*/generated/*.scene.json`). Scene `diagnostics` on `02` hold no entry about the legend.

Cause, read from the code (inferred from reading, then confirmed by the numbers above; reproduction by the new tests is a slice acceptance item):

1. **What is measured is not what is drawn.** `usecases/render_review.py:_source_inputs` builds the `legend` `SourceInput` from `detail.legend` labels, and for a colour scale from the raw field values (`bus`). `review/v05_content.py` builds the drawn `legend_entries`, and since #427 a scale entry is drawn with the entity title (`Spacecraft bus`). The two lists disagree.
2. **Only the label is measured.** `measure_sources` takes the widest text run. `place_legend` draws each entry as swatch, gap, label, so the slot is narrower than its widest entry by `swatch + gap` (for a block legend), and an inline legend is sized by one label instead of the sum of its entries.
3. **Nothing bounds a content-sized slot by its container, and nothing reports a shrink.** `engine._linear` gives a `content` cross-axis slot its preferred size even when the container is narrower (it warns `W_LAYOUT_VISIBLE_OVERFLOW` only for the overflow case). `surface_legend.emit_label` ellipsizes under `overflow: ellipsize-with-source` and records nothing, so the Scene has no trace.
4. **No gate.** `check_scene_perceptibility` does not look at text content.

Unverified: the exact widths after the fix (to be read from regenerated Scenes), and the rendered result of `02`, `12`, `15` (rendered images are read in the verification slice).

## 2. Literal acceptance (copied from the issue)

1. **General rule.** A slot declared `inlineSize: content` resolves at least to the natural width of its widest entry, up to the space its container offers. It is tested on synthetic legends: short, long and mixed entries, and containers narrower and wider than the content.
2. When a label is ellipsized anyway (content wider than the container), the Scene carries a diagnostic naming the primitive, its natural width and the available width. Silent ellipsis stays possible only where a Layout Profile explicitly opts into it.
3. A mechanical check over committed evidence fails when a `legend:*` text ends in `…` without that diagnostic. This follows the pattern of the perceptibility gate, so no eyeball review is needed.
4. **Corpus evidence, not a core criterion.** `02`, `12` and `15` are regenerated and read in full. Where a corpus slide still truncates, it is fixed in that slide's Layout YAML with an existing knob. If no knob exists, one is added as a general declaration.

## 3. Dependencies and neighbours

- [#499](https://github.com/tya5/chrona/issues/499) (Editorial legend keys): read for shared mechanism. Its three parts are zero bounds on relation keys (Scene serialization of `legend-swatch:<role>` relation primitives), the swatch aspect rule (B) and Editorial fill/outline (C). The decision on whether to take any of it is in section 4, use case U6.
- #582 (named date ranges), #492 (axis), #718 (packaged presets and parts): other agents' files. This work does not touch `axis*`, the date-range resources, `src/chrona/resources/presets/**` or preset schemas.
- #445 (side-panel text escapes made diagnosable) is the mirror case and the precedent for a typed `FitWarning` in a side slot.

## 4. Design plan

### Use cases

- **U1.** A wallboard author declares the legend slot `inlineSize: content` in a column that is wide enough. The slot is exactly as wide as its widest entry (swatch, gap, drawn label) and nothing is ellipsized.
- **U2.** The same legend in a column that is too narrow. The slot is the column width, labels are ellipsized, and the Scene says which label, how wide it wanted to be and how much room it had.
- **U3.** An inline (horizontal) content-sized legend: the natural width is the whole line of entries, and when `itemMinInlineSize` is declared the smallest useful width is the widest single entry.
- **U4.** A colour-scale legend: entries are measured with the title that is drawn, not the raw field value.
- **U5.** A reviewer or CI run checks committed Scenes mechanically for a truncated legend text without a diagnostic.
- **U6.** #499: decide whether any of its parts shares this mechanism.

### Open decisions (each is decided in the design, with the choice recorded on the issue)

- **D1. Where the legend's natural size comes from.** Option A: keep `measure_sources` text-only and add the swatch width in the engine. Option B: the legend producer in Layout (`surface_legend`) builds the `SourceInput` from the same entries and the same swatch geometry that `place_legend` uses, so measurement and drawing share one function.
- **D2. What "up to the space its container offers" means.** Clamp every `content` slot, or only slots whose declared `overflow` already says the content may shrink (`ellipsize-with-source`, `clip-optional`). A `visible-overflow` slot keeps today's behaviour (grow past the container, warn).
- **D3. How a shrink is reported.** Reuse `W_LAYOUT_VISIBLE_OVERFLOW` (wrong: nothing is drawn past a box) or add a typed `FitWarning` code for text shrunk inside its box.
- **D4. "Silent ellipsis only where a Layout Profile opts into it".** Add a new `overflow` value, or define the existing `ellipsize-with-source` as the opt-in to ellipsis and always report it.
- **D5. Where the entry list is built.** One function shared by measurement and drawing, replacing the two copies in `render_review` and `v05_content`.
- **D6. The gate's form and home.** A new checker beside `check_scene_perceptibility` and a `conformance/run_conformance.py` check, or an addition to the perceptibility evaluator.

### Responsibility boundaries

- Domain and View supply the legend entries (role and label) unchanged.
- Layout owns every size: swatch geometry, entry advance, slot size, shrink, and the typed warning. No Scene or adapter code decides a width.
- Scene carries the completed texts and the existing `diagnostics` list; it gains no field.
- The gate reads committed Scene JSON only (Scene diagnostics plus primitives), as the perceptibility gate does.

### Data and resource model, migration

- No Project, View, Theme or Layout Profile schema change is planned (D4 decides this; the plan expects none). Spec 56 section 3.2 applies if D4 chooses a new keyword.
- One new diagnostic code if D3 chooses it: it needs a message in `usecases/diagnostic_messages.py`, an entry in the generated diagnostic inventory (regenerated by the derived sync), and a Spec 33 and Spec 50 line.
- Behaviour change: legend slots that were too narrow become wider. Every committed Scene with a `legend` slot is regenerated and each changed one is reviewed against the general rule (not against byte identity). Other agents' branches see no source conflict because no shared file besides `render_review.py` and `sources.py` is edited.

### Design review questions

1. Does one shared entry-and-geometry function keep Layout the only owner of legend size, and does it avoid a second place that knows the swatch table?
2. Does clamping only shrink-policy slots leave `visible-overflow` slots (title, table) exactly as they are?
3. Does the new typed warning fit the `FitWarning` contract (placement identity, required and available inline) and the Scene `diagnostics` string form `CODE:placement_id`?
4. Is the measurement independent of the Layout Profile except through the legend slot's own declared `direction`, `gap`, `itemMinInlineSize` and `overflow`?
5. Does reordering `resolve_layout_profile` before `measure_sources` in `render_review` change any error precedence that a public test or the diagnostic inventory pins?

### Acceptance evidence

- Synthetic unit tests with no `examples/` input: short, long and mixed entries; container narrower and wider than the content; block and inline directions; a scale entry measured with its title; engine clamp for shrink-policy slots and not for `visible-overflow`; diagnostic fields (primitive, natural width, available width) on ellipsis; no diagnostic when nothing is ellipsized.
- Gate tests with synthetic Scene documents: fails on a truncated `legend:*` text without the diagnostic, passes with it, passes with no truncation; mutation check of each new test.
- Regenerated Scenes and SVGs for the corpus, a batch diff, and rendered images of `02`, `12`, `15` (and any other changed slide) read in full.
- Conformance, the affected public materializers, and the exact-main three-OS run.

### Order of design slices

1. **D497-1** (this PR): baseline and design plan.
2. **D497-2**: design and architecture review: decisions D1 to D6, the Spec 33 and Spec 50 amendments, the owner decision comment on the issue.
3. **D497-3**: implementation plan (slices, owned files, tests, generated evidence).
4. Code slices as planned in D497-3; then the acceptance review.

## 5. Design

Decisions D1 to D6 of section 4 are taken as follows. Each is an owner-level judgement recorded on the issue with options, choice, reason and how to reverse it.

### 5.1 One legend entry function (D5)

`review/v05_content.py` gains one public function that returns the drawn legend entries, `(role, label)` pairs: the Detail Profile legend, then one entry per used colour-scale value, labelled with the entity title when the Project declares one. `normalize_v05_surface_content` calls it for `legend_entries`, and `render_review._source_inputs` calls it for measurement. The second copy (labels from `detail.legend` plus raw scale values) is deleted, so measurement and drawing cannot disagree again.

### 5.2 Layout measures the legend it will draw (D1, U1, U3, U4)

`surface_legend.py` becomes the only owner of the swatch table and of the entry advance:

- `swatch_extent(role, tokens, mark_block_size, legend_size)` is `swatch_geometry` lifted out of `place_legend` with unchanged behaviour (point, mark, line, legacy buckets). `place_legend` calls it, so drawing and measuring use one function.
- `legend_source_input(entries, *, tokens, mark_block_size, arrangement)` returns the `SourceInput` of the `legend` source. Each entry is one `SourceTextRun` whose `inline_advance` is its swatch width plus the item gap, so its measured width is exactly swatch, gap, drawn label. `arrangement` is the legend slot's own declared `direction`, `gap`, `itemMinInlineSize` and `overflow`, read from the resolved Layout Profile (`legend_arrangement(resolved_profile)` finds the slot node and its resolved distances).
- `SourceInput` gains `run_flow` (`stack` or `line`, default `stack`), `run_gap` (default 0) and `min_inline` (default none). `measure_sources` measures a `stack` as the widest run (today's rule, now including the advance) and a `line` as the sum of the runs plus `run_gap` between them. A producer-declared `min_inline` replaces the default minimum (`min(preferred, widest run)`); a source that does not set it measures exactly as before.
- The legend's `min_inline` is the declared floor of shrinking. Under `overflow: ellipsize-with-source` it is the widest swatch plus gap plus the width of one ellipsis (a label can always be reduced to that), and for a `line` with `itemMinInlineSize` it is the widest single entry plus its swatch. Under any other overflow it is the preferred size, so the slot is never smaller than its content.

Label width is measured with the same treatment as drawing (`legend` role, letter spacing, text transform). `measure_sources` does not pass the numeric-spacing mode that `emit_label` passes; for a legend label that differs only when a Theme declares tabular numerals for the legend, and the result is then an ellipsis that the new diagnostic reports, not a silent one.

`render_review` resolves the Layout Profile before it measures sources (`resolve_layout_profile` needs only the set of source names), builds the legend `SourceInput` from the resolved legend slot, and measures once. Nothing else in the measurement order moves.

### 5.3 A shrinkable content slot is bounded by its container (D2, U2)

In `engine._linear`, when a child slot's cross-axis size is `content`, its `overflow` is `ellipsize-with-source`, and its source is one whose composer shrinks to the allocated width and reports it (a closed set in Layout, today `legend`), the used cross size is `min(preferred, container cross size)`. Every other slot is unchanged: a `visible-overflow` slot (title, table) keeps growing past its container and warning `W_LAYOUT_VISIBLE_OVERFLOW`; `summary` and `notes` declare `ellipsize-with-source` in the corpus but their composers do not shrink, so they stay outside the set and keep their warning. Adding a source to the set is one line and is made when its composer gains the same report. Reverse: delete the set, and a too-wide legend grows past its column and warns `W_LAYOUT_VISIBLE_OVERFLOW` instead.

The clamp resolves "up to the space its container offers". The leaf check `rect < measure.min_inline` still warns `W_LAYOUT_VISIBLE_OVERFLOW` when even the declared floor does not fit.

### 5.4 Every ellipsis is reported (D3, D4)

`surface_legend.emit_label` appends `FitWarning("W_LAYOUT_TEXT_ELLIPSIZED", placement_id, role, "legend-text", "ellipsize-with-source", natural_width, block_size, available, slot_block_size)` whenever it replaces a label with its ellipsized form. The existing machinery then carries it: `surface.fitWarnings` has the primitive id and the natural and available inline sizes, and the Scene `diagnostics` list has `W_LAYOUT_TEXT_ELLIPSIZED:{"failureKind":"legend-text","placementId":"legend:<role>","sourceRef":"<role>"}`. The code gets a cause string in `usecases/diagnostic_messages.py` (`"text was shortened with an ellipsis to fit its box"`), so the CLI warning reads like the other fit warnings.

D4 decision: no new `overflow` keyword. `ellipsize-with-source` is the Layout Profile's explicit opt-in to an ellipsis, and that opt-in does not include silence: an ellipsis cannot occur without the diagnostic. This satisfies "silent ellipsis stays possible only where a Layout Profile explicitly opts into it" by making no place silent; a profile that wants silence has no spelling for it. Reverse: add an enumerated `overflow` value (for example `ellipsize-silent`) to the Layout Profile schema under Spec 56 section 3.2 and skip the warning for it. No schema changes now, so `schema_equivalence` has nothing to compare.

### 5.5 The gate (D6, U5)

`tools/check_legend_truncation.py` reads every manifest-declared Scene (`tools.derived_evidence.scene_paths`, as `check_scene_perceptibility` does). For each text primitive whose id starts with `legend:` and whose `text` ends in the ellipsis character, the Scene must carry a `W_LAYOUT_TEXT_ELLIPSIZED` diagnostic for that placement id, and the surface `fitWarnings` entry for the same placement must show `requiredInline` greater than `availableInline`. A missing diagnostic or a contradicting entry is an error; the tool prints one line per error and a PASS or FAIL summary, with `--format json` like its sibling. It is registered in `conformance/run_conformance.py` as `legend-truncation`. A truncated legend that carries its diagnostic passes; fixing such a slide is acceptance row 4, separate evidence.

### 5.6 #499 (U6)

Decision: **leave #499 entirely.** Its three parts are zero bounds on `legend-swatch` relation keys (a Scene serialization defect for relation primitives), the swatch aspect rule (swatch geometry and Theme) and Editorial fill and outline (a preset change, in #718's area). This work reads the swatch table and changes neither a swatch shape nor a Scene bound. The #497 gate reads text and diagnostics, not swatch bounds, so it does not depend on the relation-key fix, and the measured width uses the swatch's declared extent, not its Scene bounds. No mechanism is shared. #499 stays open and unchanged; `swatch_extent` is the natural place for its part B.

### 5.7 Specifications

- Spec 33 section 6: "the decision in Scene metadata" becomes concrete: a shrunk text carries `W_LAYOUT_TEXT_ELLIPSIZED`. A `content` slot declared `ellipsize-with-source` whose source shrinks is bounded by its container. The legend paragraph states the measured legend entry (swatch, gap, drawn label) and that measurement and drawing use the same entries.
- Spec 50 section 3.1: the `ellipsize-with-source` sentence names the warning for any text the composer ellipsizes.

## 6. Architecture review

- **Ownership.** Layout owns the legend's size, its shrink and its warning; View and Domain supply entries unchanged; Scene gains no field; the gate reads Scene JSON only. The one shared function (`swatch_extent`) removes mixed ownership: before, measurement and drawing each had their own idea of the legend width.
- **Layering.** `render_review` (use case) calls Layout functions and a review-content function and adds no geometry. `sources.py` gains three optional fields on a Layout input type and no Scene import. `tools/check_import_direction.py` is expected to stay green: `surface_legend` imports `sources` types, as other `layout` modules do.
- **Regression surface.** Measurement of every source other than `legend` is unchanged by construction (new fields default to today's behaviour). The engine clamp touches only `legend` slots declared `content` plus `ellipsize-with-source`. A committed Scene can change only where it has a legend slot; the verification slice regenerates every such Scene and reviews each against the general rule.
- **Error precedence.** `resolve_layout_profile` moving ahead of `measure_sources` would change which error is reported for a document with both a Layout Profile error and a metric or font error. Implementation keeps the old precedence: a `LayoutError` from the early resolution is held, the legend is measured with the default arrangement, and the held error is raised after measurement. A test pins it (section 8).
- **Corpus.** Preset layouts (`src/chrona/resources/presets/**`) are not edited (#718). An Editorial legend is `inlineSize: fill` and `direction: inline`, so it measures as a `line` but is not content-sized; its Scene can change only if it overflows (then it reports).
- **Open risk.** A legend whose container is narrower than the swatch plus the ellipsis still warns `W_LAYOUT_VISIBLE_OVERFLOW` at the leaf; that is the honest limit and is covered by a test.
- **Extension points.** New legend roles reach `swatch_extent`; new shrinking composers join the closed set of 5.3 together with their report; a silent opt-in has a defined reversal (5.4).

## 7. Implementation plan

Three code publications, each its own PR with `Refs #497`. The generated Scene and SVG evidence is regenerated by the derived sync after each merge; PRs carry no generated output. Locally, evidence is regenerated into a scratch directory to inspect it.

### I497-1: measure, bound and report (the core rule)

- **Files.**
  - `src/chrona/presentation/review/v05_content.py`: public `legend_entries(detail, project, projection, color_scale)`; `normalize_v05_surface_content` uses it.
  - `src/chrona/presentation/layout/surface_legend.py`: `swatch_extent`, `legend_source_input`, `legend_arrangement`; `place_legend` uses `swatch_extent`; `emit_label` appends the `W_LAYOUT_TEXT_ELLIPSIZED` fit warning.
  - `src/chrona/presentation/layout/sources.py`: `SourceInput.run_flow`, `run_gap`, `min_inline`, and their use in `measure_sources`.
  - `src/chrona/presentation/layout/engine.py`: the clamp of 5.3 (closed set `legend`).
  - `src/chrona/usecases/render_review.py`: resolve the Layout Profile first, build the legend `SourceInput` from the shared entries and the resolved legend slot, delete the old legend measurement.
  - `src/chrona/usecases/diagnostic_messages.py`: cause string for the new code.
  - Not touched: schemas, presets, themes, any `examples/` file, axis and date-range code.
- **Tests (synthetic, no `examples/` input).**
  - `tests/unit/chrona/presentation/layout/test_legend_measurement.py`: `legend_source_input` and `measure_sources` for short, long and mixed entries, `stack` and `line`, with and without `itemMinInlineSize`, a swatch of each bucket, and the declared minimum under each overflow.
  - `tests/unit/chrona/presentation/layout/test_intent_engine.py` additions: the clamp for a `legend` slot (container narrower and wider than the content), no clamp for a `legend` slot declared `visible-overflow`, no clamp for a `summary` slot declared `ellipsize-with-source`.
  - `tests/unit/chrona/presentation/review/test_v05_content.py` additions: `legend_entries` returns the drawn labels (title for a scale value, raw value when the entity is absent), and measurement and drawing receive the same list.
  - `tests/integration/test_legend_slot_sizing.py`: end to end through `tests/support/synthetic_review.py` with a project whose entity titles are long and a Layout Profile with a `content` legend in a sidebar. Wide sidebar: no label ends in an ellipsis, the legend slot equals the widest entry, no `W_LAYOUT_TEXT_ELLIPSIZED`. Narrow sidebar: every shortened label has one `W_LAYOUT_TEXT_ELLIPSIZED` diagnostic whose placement id is the label and whose `fitWarnings` entry has `requiredInline` equal to the natural width and `availableInline` equal to the room; the slot stays inside the sidebar.
  - A test that a document with both a metric error and a Layout Profile error still reports the metric error (the order before this work), written against the old order first.
  - `tests/unit/chrona/usecases/test_diagnostic_messages.py` (or `test_warning_messages.py`): the new code has a described cause.
- **Mutation checks.** Each new test is run against a deliberately broken implementation and must fail: drop the swatch advance; measure raw values instead of titles; sum instead of max for `stack`; remove the clamp; clamp a `visible-overflow` slot; drop the warning; report the wrong placement id; swap required and available. Results are listed in the PR description.
- **Generated evidence.** Regenerate every public materializer into scratch with `tools/regenerate_public_examples.py`, diff Scenes and SVGs against `main`, and review every changed slide against the general rule (a legend as wide as its widest entry, never wider than its column, nothing ellipsized unless a diagnostic says so). Rendered images of `02`, `12`, `15` and every other changed slide are read in full, and the result is recorded in this record (section 8). Byte identity is evidence only for the slides that must not change (those without a legend slot or with a legend that already fitted).
- **Acceptance gates.** Focused tests; `conformance/run_conformance.py`; `tools/check_import_direction.py`; `tools/regenerate_public_examples.py --check` against the regenerated scratch output for the slides expected to change; the PR checks including `derived-ready`.
- **Publication boundary.** One PR; merged with the merge lock; the next slice bases on the derived-sync bot commit that follows it.

### I497-2: the mechanical gate

- **Files.** `tools/check_legend_truncation.py`; `conformance/run_conformance.py` (`legend-truncation` check); `tests/unit/tools/test_check_legend_truncation.py`.
- **Tests.** Synthetic Scene documents: a truncated `legend:*` text with the diagnostic and a matching `fitWarnings` entry passes; the same text without the diagnostic fails; a diagnostic whose `fitWarnings` entry has `requiredInline` not greater than `availableInline` fails; a legend with no ellipsis passes; a non-legend text ending in an ellipsis is ignored; an unreadable Scene is a named error; output is stable and UTF-8. Mutation checks: ignore the diagnostic; match any `W_LAYOUT_TEXT_ELLIPSIZED`; match the wrong placement; ignore `fitWarnings`.
- **Real evidence.** After I497-1 the derived sync has regenerated the committed Scenes; the gate passes on `main` with the corpus as it is. Before I497-1 the gate would fail on `02`, `12`, `15` (recorded as the before-state with the command output).
- **Order.** After I497-1 and its derived-sync commit, so conformance on the PR and on `main` is green.

### I497-3: corpus read, acceptance review

- Read the regenerated `02`, `12` and `15` as images and Scenes. If a corpus slide still truncates, fix it in that slide's Layout YAML with an existing knob (for example the sidebar width token or the legend slot's `itemMinInlineSize`/`direction`); if no knob exists, stop and add a general declaration through the design path first. Corpus data (`project.yaml`, entity titles) is never edited to pass a render criterion.
- Write the literal acceptance review (`docs/reviews/current/issue-497-legend-slot-sizing-acceptance-review-<date>.md`, `<!-- chrona:literal-acceptance/v1 -->`, one row per criterion of section 2, successor links for any narrowed or deferred row), merge it, locate the exact-main three-OS run on the review commit, and close only when full-matrix (ubuntu, macOS, Windows) and `reproduction-newest-python` are green on that commit.

## 8. Progress and evidence

### I497-1 (implemented)

- **Behaviour change.** Regenerating all 29 public slides locally against `main` changes exactly three: `02-programme-board`, `12-glyph-gates`, `15-gallery-image-notes`. The only Scene differences are the `legend` slot (inline size 64.6 px to 217.3 px, inside a 420 px sidebar) and the nine `legend:*` texts (text and bounds). Nothing else in those slides moved. Every other slide is byte-identical, which is evidence only that no other slide has a legend that was too narrow, not a quality bar.
- **Measured against the general rule.** In each of the three, every `legend:*` text is its full label, none ends in an ellipsis, the slot is the widest entry (swatch, gap, "Assembly, integration and test"), and no `W_LAYOUT_TEXT_ELLIPSIZED` is emitted (no label is shortened). Rendered images of all three were read in full: nine legend rows, each legible; the owner colours are readable by name; the rest of each slide is as before.
- **An inline legend's block size.** An early version also changed the block size of an inline legend's slot (a line measured as one row instead of a stack of rows). That moved four more slides (`03`, `13`, `14`, `16`) and is not part of #497 (it depends on how a wrapping line breaks), so the block measurement stays the stack of every run and only the inline size changed. Recorded here so a successor does not mistake it for an omission.
- **Tests.** `tests/unit/chrona/presentation/layout/test_legend_sizing.py` (measurement, floor, arrangement, clamp), `tests/integration/test_legend_slot_sizing.py` (end to end on the synthetic Project: roomy and narrow sidebar, non-shrinking legend, error precedence), additions to `test_v05_content.py` and `test_warning_messages.py`. No test reads `examples/`.
- **Mutation checks (all killed).** Dropping the swatch and gap advance; measuring the raw value instead of the title; summing instead of taking the widest for a block legend; summing replaced by widest for an inline legend; removing the clamp; clamping regardless of the overflow policy; clamping every source; dropping the warning; naming the role instead of the placement in the warning; swapping required and available; dropping the declared floor; ignoring the ellipsis in the floor; ignoring the gap; raising the Layout Profile error before measurement.
- **Gates run locally.** The non-corpus suite (4151 passed, 28 skipped), the corpus-marked tests (24 passed) and conformance, where only `diagnostic-inventory` is stale, as for any source change: the inventory carries source line numbers and is regenerated by the derived sync, so it is not edited by hand.

### I497-2 (implemented)

- **Gate.** `tools/check_legend_truncation.py` (registered in conformance as `legend-truncation`, between `scene-perceptibility` and `starter-perceptibility`). For each `Text` primitive whose id starts with `legend:` and whose `text` or laid-out line ends in the ellipsis, it requires a `W_LAYOUT_TEXT_ELLIPSIZED` entry in the Scene `diagnostics` for that placement id (`E_LEGEND_TRUNCATION_UNREPORTED` otherwise) and a surface `fitWarnings` entry for the same placement with `requiredInline` greater than `availableInline` (`E_LEGEND_TRUNCATION_FACTS` otherwise). An unreadable Scene is `E_LEGEND_TRUNCATION_DOCUMENT`.
- **Before and after on the real corpus.** On the committed Scenes before the derived sync regenerates them (the evidence of `4981db0a`) the gate reports 24 errors: the eight truncated labels of each of `02`, `12`, `15`, every one `E_LEGEND_TRUNCATION_UNREPORTED`. On the Scenes regenerated with I497-1 it prints `Legend truncation: PASS (0 errors)`.
- **Tests.** `tests/unit/tools/test_check_legend_truncation.py` on synthetic Scene documents (pass with diagnostic and facts; fail without the diagnostic; another primitive's diagnostic does not cover it; missing, equal or wrongly coded facts fail; no ellipsis passes; other texts and non-text primitives are ignored; ellipsis only in `text` or only in the lines counts; malformed diagnostic payload is not a report; every text reported once; unreadable Scene named; UTF-8 transport) and the order assertion in `tests/unit/tools/test_run_conformance.py`.
- **Mutation checks (all killed).** Ignoring the diagnostic; accepting any ellipsis diagnostic; ignoring the facts; accepting an equal shortage; matching any text id; matching any fit-warning code; ignoring the laid-out lines; ignoring the text field; counting non-text primitives; swallowing unreadable Scenes. Two of these first survived (ignoring the text field; counting non-text primitives) and led to two added tests.

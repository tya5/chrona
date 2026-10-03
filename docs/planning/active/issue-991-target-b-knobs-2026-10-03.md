# Issue #991: the knobs approved target B still needs (work record)

Living record for [#991](https://github.com/tya5/chrona/issues/991): baseline, design plan, design, architecture review, implementation plan and progress. Edited in place; Git keeps history. Found by the reviewer's YAML-only target-B reproduction ([#987](https://github.com/tya5/chrona/issues/987), PR #993). The target is the owner-approved mock `docs/research/presentation/halcyon-1-target-design-2026-09-21/board/02-programme-board.png`.

**Public base:** `016a26c1` on `main`. **Status:** design plan, design, architecture review and implementation plan are published together by this record (PR #999); every slice is merged except the relation entry side (item 15, successor #1030); the [acceptance review](../../reviews/current/issue-991-target-b-knobs-acceptance-review-2026-10-03.md) is published.

**Scope rule (owner, 2026-10-03):** this work changes core knobs and their own evidence only (synthetic tests and a Controller Z evidence slide). It does **not** edit the reviewer's `21-target-b` files (`examples/halcyon-1` views, themes, layouts, schemes, profiles, contexts); adopting each knob there is the reviewer's step and not an acceptance row here.

## 1. Published baseline

Read on `16c9de36` from code and specifications (agents read the code; nothing below is inferred from images):

1. **Ghosts.** `projection._compose_rows` adds a baseline member only for `comparison.baseline: scenario` in automatic rows; the snapshot data is already loaded and passed to it but read only for explicit rows, which forbid `grouping`. The enum value `snapshot` exists and is a drawing no-op in automatic rows. Ghost drawing (shared track, `snapshot` role, `baseline` gate variant) is complete downstream.
2. **Title.** The only producer is `render_review.py:713` (`project.title`, one `heading` line). `heading` and `subtitle` typography roles exist in Themes; no subtitle producer exists. The Project calendar has an id but **no name or title** (`project-v0.7`).
3. **Hatch.** `missing-actual` is derived for `DUE_UNOBSERVED` (planned end/at <= as-of, no observation) and drawn as a small bar at the planned due endpoint for spans and gates alike. An open actual span (`start`, no finish) is `RECORDED` and draws only the `actual` open-span. `06-view-model` says a start-based obligation "requires a future versioned View policy". A catalogue pattern bound to `missing-actual` crashed the legend swatch (fixed by #997).
4. **As-of chip.** Placement candidates are top-end, top-start and rule-hosted (`asof_label.py`); no bottom candidate. `markers[].date.form` is `const: localized-date` (`Aug 20, 2027`); the name tables carry 13 closed forms, none `day month`.
5. **Order.** `ordering.by` is `id|title|plannedStart|plannedEnd`; `_order` and `_network_order_key` are the two sort sites. Declaration order is `project.objects` key order.
6. **Gates** take the `planned` visual role. `milestone` is already a registered Theme role used only by the legend swatch, and several bundled Themes bind colours for it, so reading it for gates would change their output.
7. **Note header/leader.** `annotationKinds.color` reaches only bar, accent and stamp (`v05_builder._complete_primitive_paint`). `{subject}` is the anchored object's title ("" for a non-item anchor).
8. **Exception days** are drawn with `semanticId calendarClosed`; the orange exists only in the legend swatch (an unregistered open legend role).
10. **Note padding.** `contentInsetEm` is in the Theme schema for every outline but is parsed and used only for `outline: image` (`theme_tokens.py`, `surface_annotations.py:325`).
12. **Legend (bug).** The inline legend branch places the swatch at the row top and the label baseline at `y + legend_size`; the vertical branch already centres both on the line box.
13. **Table header** is bound to the shared `text` role and hard-coded as `"text"` in `surface_table.py` and `presentation.py`.
14. **Colour scheme.** The intent vocabulary is closed and repeated in `color_scheme.py`, `color-scheme-v0.2`, both Theme `colorBindings` enums and the annotation-kind check. No preset binds a rule colour; axis rule and separators bind `text` and `surfaceRaised`.
9. **Δ column.** `missing` is one closed enum for the column; `in-progress` shows "in progress" while a span is active, else a hard-coded em-dash. Unobserved-blank with in-progress-dash cannot be said.

Unverified: rendered looks of every knob; corpus bytes after each slice (read per slice); whether the Project loader and the authoring writers preserve `objects` order (S5 tests it).

## 2. Literal acceptance (copied from #991)

| # | Criterion |
| --- | --- |
| A1 | Each item lands as a general knob or fix with synthetic tests, or is declined with a reason. |
| A2 | Item 3's legend crash is fixed regardless. |
| A3 | After each landing, the reviewer updates the #987 YAML. Do not change the target-B files yourself. |

Items: 1 ghosts with grouped rows; 2 title and subtitle; 3 in-progress hatch; 4 as-of label placement and date form; 5 source order; 6 gate paint; 7 kind colour on note header and leader (and `{subject}` as id); 8 exception paint; 9 per-state delta text; 10 note padding; 11 (= 7); 12 legend swatch centring (bug); 13 table-header role; 14 line colour intent. A3 is the reviewer's step (owner direction above); my row records that the knob exists and is documented.

## 3. Dependencies and neighbours

- #583 (group header template), #584 (annotation kinds), #588 (affixes), #428 (as-of chip), #427/#497 (legend), #718 (catalogue patterns), #880 (plot), #893 (calendar) are reused unchanged.
- #970 (schema_equivalence tooling) and #995 (contrast gate files) are other agents' work; this work edits neither. Expected-delta entries for my schema edits are kept correct per slice.
- Shared files (`view-v0.28`, `theme-v0.11/0.13`, `color-scheme-v0.2`, `expected-deltas-v0.1.yaml`, `capabilities.py`, `semantic_registry.py`) are rebased carefully before every push.

## 4. Design plan

Use cases (all on synthetic Projects; target B is the comparison, never the oracle):

- **U1** a grouped, automatic-row board with baseline ghosts (1); **U2** a slide with a declared heading and subtitle with the as-of date (2); **U3** an in-progress span hatched up to as-of and gates plain (3); **U4** a chip at the plot foot reading `20 Aug` (4); **U5** rows in declaration order (5); **U6** black gates distinct from blue bars (6); **U7** note headers and leaders in the kind colour (7); **U8** exception days in their own colour (8); **U10** padded rectangle notes (10); **U12** centred swatches (12); **U13** a muted small-caps header (13); **U14** a rule colour (14); **U9** blank unobserved, dash in-progress (9).
- **Every knob is optional and absent means today's output byte for byte.** Spec 56 section 3.2 applies: additive optional View and Theme properties go in place with no version bump; `default` annotations implement nothing; the consumer supplies and tests the omission behaviour; each schema slice runs `python -m tools.schema_equivalence --base-rev origin/main` and records the result.

## 5. Design (decisions; reverse = delete the optional property and its consumer branch)

| Slice | Decision | Why / alternatives rejected |
| --- | --- | --- |
| S1 ghosts | New optional `comparison.baselineMarks: ghost` (absent = none). With `baseline: snapshot` and the switch, `_compose_rows` appends a shared-track snapshot member per primary item present in the snapshot (id `snapshot:<oid>`, as the scenario member does). Works for automatic, field-grouped and lane rows because grouping lives on the primary item. Switch without a snapshot in the closure fails with the existing missing-snapshot diagnostic. | Making `baseline: snapshot` itself emit ghosts would change HALCYON-1 view 07 and the gallery; explicit rows cannot be relaxed (they forbid `grouping` by design). |
| S2 heading | New optional View `heading: {title, subtitle}` templates. Placeholders `{project}`, `{asOf}` (the as-of marker's date form), `{calendar}` (the calendar **id**; the Project calendar has no name and adding one is a Project schema change, left to a successor if wanted). One shared brace parser extracted from `group_header_text` and `annotation_kind_text` is **not** done here (separate refactor); the heading engine reuses `group_header_text.parse_template` with its own placeholder set. Rendered in the content layer; the existing `title` source carries two runs (`heading`, `subtitle` roles, stacked), so no new slot source. Table-timeline only; `dependency-network` ignores it (documented). Unknown placeholder: `E_VIEW_HEADING_TEMPLATE`. | A new `subtitle` slot source would be a Layout Profile enum change for no gain. |
| S3 hatch | New optional `comparison.missingActualScope: due-unobserved \| in-progress` (absent = `due-unobserved`, today). `in-progress`: a **span** with an actual start, no finish and an as-of draws the `missing-actual` mark as a span from actual start to as-of (the open-span geometry, under the actual mark) and no mark for gates. A separate derived flag on the item, not a new `ObservationState`, so the lane and table consumers of `RECORDED` are untouched. | A new state would ripple into lane closure, `table_value` and the summary counts. A per-type list is deferred: spans only is the use case. |
| S4 chip | Marker gets optional `placement: top \| bottom` (absent = top); `date.form` widens from `const` to `enum [localized-date, day-month]`; `day-month` is an optional form in the name tables (built-in tables carry `{day} {monthShort}` / `{monthNumber}月{day}日`); a custom table lacking it fails with a typed diagnostic only when the form is used. Bottom adds `plot-bottom-end/start` candidates to the as-of solver. | Making `day-month` a required table form would break every custom table. |
| S5 order | `source` added to `ordering.by` (and `tieBreak`); `_order` and `_network_order_key` take a `source_index` built from `project.objects` order. | Silent fall-through in the network key is the named risk; both sites are tested. |
| S6 gates | New optional Theme role `gate` (visual role for primary/combined point marks when the Theme declares it; purpose stays `planned`, so lanes, interaction and perceptibility sets are unchanged). The legend point key uses `gate` when declared. | `milestone` is already bound in bundled Themes; reusing it changes their bytes. A new name needs no regeneration. |
| S7 note | Optional per-kind `colorApplies` list (`bar, accent, stamp, header, leader`; absent = the three today) in `annotationKinds`; Scene applies the kind paint to header text and leader accordingly. `{subjectId}` placeholder resolves the anchor id (`{subject}` stays the title). The Scheme-time kind contrast gate is re-run on the text colour; no gate is weakened. | Changing `{subject}` would alter existing Themes. |
| S8 exception | `calendarException` semantic id emitted for exception days **only** when the Theme declares `calendar-exception` with a `backgroundTreatment`; otherwise `calendarClosed` as today. Registered as a decoration role; the committed evidence slide paints it (decoration witness). | Colour-only difference needs a role, not a flag. |
| S10 padding | `contentInsetEm` parsed and applied for every outline (rectangle, balloon, image); absent = zero. | Schema already admits it. |
| S12 legend | The inline branch computes `item_height = max(swatch, line box)` and centres swatch and baseline on it, as the vertical branch does. Plain bug; goldens move. | |
| S13 header | New Theme text role `tableColumnLabel`, registered in `capabilities.py`; Layout resolves it with a fallback to `text` when the Theme does not declare it (`has_role`); header block height and column minimums use the resolved treatment. | A fallback keeps every committed Theme identical. |
| S14 line | Optional Scheme colour `rule` (not in `required`), allowed in Theme `colorBindings` enums. A Theme binding `rule` against a Scheme that does not declare it fails with `E_SCHEME_INTENT_UNKNOWN`; no hidden fallback. | One intent is enough for the use case; separators bind the same intent. |
| S9 delta | Optional column `missingBy` map from observation state (`inProgress`, `notYetDue`, `dueUnobserved`, `unavailable`) to the `missing` enum; omitted = today. The state is classified once in `cell_parts`; affixes still wrap the result. | |

**Owner-level calls (decided here, recorded on #991):** the `{calendar}` id limit; ghost switch name; `gate` as a new role. Reversible by deleting the property.

## 6. Architecture review

- **Layers.** Intent (View/Theme/Scheme) declares; the content layer composes text and rows; Layout owns geometry (ghost tracks, chip candidates, legend centring, header metrics); Scene applies completed paint (kind colour, `gate` role); adapters unchanged. No knob puts geometry in Scene or paint in Layout.
- **Defaults.** Every slice has a default-off byte-identity check (`regenerate_public_examples --check`); S12 is the only deliberate output change (a bug).
- **Corpus.** No corpus datum is edited; target B is evidence only; evidence slides are Controller Z Contexts, not `21-target-b`.
- **Gates.** No contrast or perceptibility gate is weakened; the contrast gate files are not touched (#995).
- **Residual risk.** S3 touches lane projection consumers; S8 adds a decoration role needing committed evidence; S2 may change title measurement for long titles (only when declared).

## 7. Implementation plan

Order (most visible first; one PR each, defaults unchanged, merged one at a time through the merge lock):

| # | Slice | Owners (files) | Schema / S0 | Tests | Evidence |
| --- | --- | --- | --- | --- | --- |
| 0 | Legend crash (done, PR #997) | `surface_completion.py` | none | `tests/integration/test_legend_catalog_pattern.py` | none |
| 1 | Ghosts with grouped rows | `contracts/resources.py`, `projection.py`, `view-v0.28` | optional property; delta if flagged | projection unit + render integration | Controller Z `baseline-ghosts` slide |
| 2 | Heading and subtitle | new `heading_text.py`, `resources.py`, `v05_content.py`, `render_review.py`, `surface_composer.py`, `v05_builder.py`, `semantic_registry.py` | optional View property | template unit, composer unit, integration | slide `heading` |
| 3 | In-progress hatch | `resources.py`, `projection.py`, `mark_geometry.py`, `presentation.py` | optional View property | geometry unit + lane + integration | slide `in-progress` |
| 4 | As-of chip | `asof_label.py`, `v05_content.py`, name tables + schema, `view-v0.28` | enum widening + optional property | solver unit, content unit | slide `as-of-foot` |
| 5 | Source order | `projection.py`, `view-v0.28`, spec 06 | enum widening | order unit incl. network | none |
| 6 | Gate paint | `v05_builder.py`, `surface_legend.py`, `capabilities.py` | none (Theme roles open) | scene unit | slide `gate-paint` |
| 7 | Kind colour | `theme_tokens.py`, `color_scheme.py`, `theme-v0.13/0.11`, `v05_builder.py`, `annotation_kind_text.py` | optional Theme property | kind integration | extend `annotation-kinds` slide |
| 8 | Exception paint | `surface_axis.py`, `surface_backgrounds.py`, `semantic_registry.py`, `capabilities.py` | none | background unit | slide `calendar-exception` |
| 9 | Note padding | `theme_tokens.py`, `surface_annotations.py` | none | annotation layout unit | slide |
| 10 | Legend centring (bug) | `surface_legend.py` | none | legend unit | goldens regenerated by CI sync |
| 11 | Table header role | `capabilities.py`, `theme_tokens.py`, `surface_table.py`, `presentation.py`, `semantic_registry.py` | none | table unit | slide |
| 12 | Line colour | `color_scheme.py`, `color-scheme-v0.2`, Theme schemas | optional Scheme property | scheme unit | slide |
| 13 | Delta states | `resources.py`, `view-v0.28`, `v05_content.py` | optional View property | content unit | slide |

Slices not reached get a short successor issue (duplicate search first). Every slice: failing test first, mutation check, read the rendered before/after of an evidence slide against the mock and state honestly how close it is, `git diff --stat origin/main` shows only the slice's files, record state on #991 after the merge.

## 8. Progress

All slices below are merged; the PR and commit of each is in the acceptance review. Items 16 (`baselineMarks: ghost-when-changed`) and 17 (the owner's in-progress rule: started on or before as-of, unfinished, progress below 1 or absent, `openUntil` sufficient) were added by the reviewer and owner during the work and landed as #1029 and #1025/#1028. Not done: item 15 (#1030), the calendar title (#1026) and the in-progress hatch with lane rows (#1027). Adoption in 21-target-b is the reviewer's (#987).

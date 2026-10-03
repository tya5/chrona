# Issues #1063 and #1066: target-B top items, as-of chip below the plot and gate symbol size (work record)

Living record for [#1063](https://github.com/tya5/chrona/issues/1063) (as-of chip below the plot, space reserved) and [#1066](https://github.com/tya5/chrona/issues/1066) (a symbol mark takes its own size and offset per role). Baseline, design plan, design, architecture review and implementation plan are published together by this record before any code. Edited in place; Git keeps history. Both were found by the reviewer's tuning PR #1061 against the owner-approved mock `docs/research/presentation/halcyon-1-target-design-2026-09-21/board/02-programme-board.png` (the work record of the knob family is [issue-991-target-b-knobs-2026-10-03.md](issue-991-target-b-knobs-2026-10-03.md)).

**Public base:** `d4b081cf` on `main` (before this record). **Status:** design plan, design, architecture review and implementation plan published; no code yet. Order: #1063 then #1066.

**Scope rule (owner):** core knobs and their own evidence only (synthetic tests and a Controller Z evidence slide). This work does **not** edit the reviewer's `examples/halcyon-1/*target-b*` files; adopting a knob there is the reviewer's step (PR #1061, #987) and not an acceptance row here. Routing/terminals (#1059, #1060, #1042, #1044, #1046) and annotation boxes (#1051, #1049) are other agents' files and are not touched.

## 1. Published baseline

Read on `d4b081cf` from code, specifications and the mock:

1. **Mock.** The chip ("as of 20 Aug") sits below the plot bottom with a small gap, centred on the dashed as-of line, which stops at the plot bottom; the legend follows below. Gates are filled black diamonds of one size; a baseline gate is a hollow diamond.
2. **Chip today.** `markers[].placement` is `top | foot` (#1006). `asof_label.find_asof_label_candidate` puts `foot` at `plot_bottom - gap - height`, inside the plot, so it covers the last row's label and marks. Nothing reserves space outside the plot. The label request, candidate names and the `placement` switch live in `surface_member_labels.py`; the content value is `SurfaceContent.as_of_placement` (`v05_content.py`).
3. **Plot and slot.** `plot_rect` (#880) is the timeline slot down to the last row's bottom, never past the slot. Rows are placed by `place_rows` inside the timeline slot with `pack` or `fill` distribution; a requested block is a minimum, so rows may extend the surface. The content-sized extent comes from `timeline_content_block_requirement` and `resolve_content_block_extent` (`render_review.py`); in a fixed viewport the timeline slot flexes and later slots keep their sizes. The axis header is its own slot (`timeline-axis`); the Layout Profile has no slot below the plot.
4. **Symbols today.** A point mark (gate or milestone) of role R is a square of side `block_size * markHeight(R)` at block `track_top + block_size * markOffset(R)` (`MarkBandFrame.role_bounds`, used by `compose_item_marks`). The actual role's band is a thin bar (`markHeight` 0.17 of the 16 px track), so an actual gate is 2.7 x 2.7 px. No Theme property sizes a symbol apart from the bar band of its role. Roles with point marks: `planned`, `actual`, `snapshot`, `scenario`; `missing-actual` is span-only. The role properties are named number tokens in `roles` of `theme-v0.13` (`theme-v0.11` is transitioning).
5. **Gates.** Containment of a role's extent in its row is checked in `place_mark_tracks` (via `minimum_track_block_extent`); lanes use the same frame through `compose_item_marks`.

Unverified (checked per slice): corpus bytes after each slice; the contrast gate and perceptibility gate on the evidence slides; the chip on lane rows.

## 2. Literal acceptance (copied from the issues)

#1063 (synthetic fixtures, published Scene):

| # | Criterion |
| --- | --- |
| A1 | With `below-plot`, the chip's top is at or below the plot's bottom edge. |
| A2 | The chip does not overlap any row, mark or legend primitive. |
| A3 | Its centre is on the as-of x. |
| A4 | The legend or footer moves down by exactly the reserved size. |
| A5 | The no-room case falls back, with the diagnostic. |
| A6 | Existing placements give byte-identical output. |
| A7 | Target B declares it, and the chip no longer covers "First light". |

#1066 (synthetic fixtures, published Scene):

| # | Criterion |
| --- | --- |
| B1 | A gate with planned and actual dates: the actual symbol's bounds equal the declared `symbolHeight` x track, at the declared offset. |
| B2 | Actual bars in the same fixture keep their `markHeight`. |
| B3 | Every role with a symbol honours the tokens. |
| B4 | The default is no smaller than the planned gate. |
| B5 | Target B regenerated: the `cdr` and `payload-delivery` actual symbols are legible diamonds, not 2.7 px dots. |

A7 and B5 are the reviewer's adoption step (owner scope rule above): my rows record that the knob exists, is documented and is shown working on a Controller Z slide, with successor #987 / PR #1061. B4 conflicts with the owner direction that new knobs default to today's output; see decision D7.

## 3. Dependencies and neighbours

#428 and #1006 (as-of marker), #880 (plot), #501/#822 (marks), #991 (knob family) are reused unchanged. #970 (schema equivalence) is tooling used as is. Shared files (`view-v0.28`, `theme-v0.13`, `expected-deltas-v0.1.yaml`, `capabilities.py`, `diagnostic_messages.py`) are rebased carefully before every push and carry minimal diffs.

## 4. Design plan

Use cases (synthetic Projects; target B is the comparison, never the oracle):

- **U1** a table-timeline slide whose as-of chip sits below the plot, the last row untouched, in a content-sized and in a fixed-height surface (pack and fill); **U2** a surface too short for the chip, falling back to the inside foot with a diagnostic; **U3** a gate with planned and actual dates whose actual diamond is as large as the planned one and overlaid on it; **U4** a Theme that sizes only the offset, or only the height.
- Every knob is optional; absent means today's output byte for byte. Spec 56 section 3.2 applies: an additive optional value or property goes in place with no version bump; schema `default` annotations implement nothing; the consumer supplies and tests the omission behaviour.

## 5. Design (decisions; reverse = delete the optional value or property and its consumer branch)

**#1063, as-of chip below the plot.**

- **D1 value.** `markers[].placement` gains `below-plot` beside `top` and `foot` (absent = `top`). The View declares intent only.
- **D2 reservation (Layout).** With `below-plot` and an as-of inside the window, Layout reserves `R = chipBlock + gap` under the last row, in the timeline slot: `chipBlock = fontSize * lineHeight + 2 * chipPaddingY` of the `asOfLabel` role (one line) and `gap = max(1, fontSize * 0.25)`, the same two values the placer uses. The helper lives in Layout (a new small module beside `asof_label.py`) and is read by both the content-sized extent and the row placement.
  - Content-sized: the timeline block requirement grows by `R`, so every following slot (legend, footer) moves down by exactly `R`.
  - Row placement: `place_rows` receives the timeline block size reduced by `R`, so under `fill` the rows give up `R`; under `pack` the rows keep their size and the strip under them is used.
  - Fit rule: the reservation fits iff `sum(required row blocks) + group headers + R <= timeline block size`. If not, Layout reserves nothing and falls back (D3).
  - The plot, and so the as-of line, ends at the last row (#880); no new rectangle is introduced.
- **D3 placement and fallback.** A new candidate set `below-plot` centres the chip on the rule with its top at `plot_bottom + gap` (legal when the box lies in the timeline slot and meets no mark, text, label visual or rule), then beside the rule (end, then start), then fails. Fallback to today's inside `foot` placement, with `W_LAYOUT_ASOF_BELOW_PLOT_FALLBACK:as-of-label`, when the reservation does not fit (fixed-height region) or no below-plot candidate is legal. The diagnostic is a surface diagnostic (curated cause in `diagnostic_messages.py`).
- **D4 (owner-level) alternatives rejected.** (a) A new `timeline-foot` slot in the Layout Profile: changes the Profile schema and every bundled Profile, and other agents edit Profiles; rejected. (b) Reserve inside the timeline slot (chosen): no schema beyond one enum value, no Profile change, the same effect for legend and footer. (c) Extending the plot below the rows: would move gridlines, the rule and the cone; rejected.
- **Contrast and perceptibility.** The label stays `asOfLabel` (ground text) and its chip `asOfLabelChip`; the gates still see both. The ground under the strip is the canvas ground, checked on the evidence slide.

**#1066, symbol size and offset per role.**

- **D5 tokens.** Optional Theme role properties `symbolHeight` and `symbolOffset` (named number tokens, ratio of the track block size, like `markHeight` and `markOffset`) on the roles `planned`, `actual`, `snapshot`, `scenario`. They apply to **point** marks (gates and milestones) of that role only; bars, open spans and the span-only `missing-actual` keep the band. Each is independent: an absent `symbolHeight` is `markHeight`, an absent `symbolOffset` is `markOffset`.
- **D6 consumer.** `MarkGeometry` carries optional `symbol_height` and `symbol_offset`; `MarkBandFrame.symbol_bounds(role)` returns the block start and side. A point mark is a square of that side, ports at its centre. Validation: effective height > 0, offset >= 0, offset + height <= 1, else `E_THEME_TOKEN_TYPE` at `/body/roles/<role>/symbolHeight` or `symbolOffset`; `place_mark_tracks` also contains the symbol extent in the row.
- **D7 (owner-level) default.** The issue asks for a default no smaller than the planned gate (B4). The owner direction for this work is that new knobs default to today's output, and a default change needs corpus regeneration, grouped diff review and images. Choice: absent tokens leave output unchanged; a Theme declares `symbolHeight` and `symbolOffset` on `actual` to overlay a full-size diamond. B4 is narrowed: a successor issue "default actual gate symbol size" (bundled Themes declare the tokens; corpus regeneration and image review) is filed after a duplicate search. Reverse: a default in `resolve_mark_geometries` (or bundled Theme tokens) instead of absence.
- **Contrast and perceptibility.** Symbols stay `Symbol` primitives of the same roles; a larger actual symbol only raises perceptibility; the contrast gate reads their paint unchanged.

**Schema (Spec 56 section 3.2; S0 gate).** `view-v0.28`: `markers.items.properties.placement.enum` widens to `[top, foot, below-plot]`. `theme-v0.13`: two optional properties in `roles.additionalProperties.properties`. Both are additive (accepted values only grow), with one expected-delta entry per pointer and a covering test; `python -m tools.schema_equivalence --base-rev origin/main` runs per schema PR and its result is recorded in the PR; `--prune-stale` retires entries that outlived their merge by more than one schema merge. Living specifications updated with the code PRs: Specification 39 (as-of chip) and the mark-geometry specification (symbol tokens), each with the migration impact (none: omitted keeps output).

## 6. Architecture review

- **Layers.** View declares the placement; Theme declares symbol ratios; Layout owns the reservation, row placement, chip candidates, fallback and symbol geometry; Scene and adapters receive completed primitives and are unchanged. No geometry in Scene, no paint in Layout.
- **Defaults.** Both slices are byte-identical when the new value or tokens are absent (`regenerate_public_examples --check` shows no corpus diff); no corpus datum is edited.
- **Adjacent designs.** Reservation reuses the plot rule (#880) and the content-sized extent path used by lanes; it adds no Layout Profile property. The symbol tokens reuse the `markHeight` family and its validation. Lanes and folded group-header points compose through the same `compose_item_marks` frame and so honour the tokens without a second path.
- **Failure behaviour.** No room or no legal candidate: fallback plus one warning, never an error. Out-of-range tokens: the existing Theme token error.
- **Residual risks.** Lane rows under `below-plot` (preflight requirement must add `R`); an as-of at a window edge (centred chip leaves the slot, so the end or start candidate is used); `fill` under a fixed viewport shrinks rows by `R`.

## 7. Implementation plan

One PR per slice, defaults unchanged, merged one at a time through the merge lock; each: failing test first, mutation check, rendered evidence read, `git diff --stat origin/main` limited to the slice.

| # | Slice | Owners (files) | Schema / S0 | Tests | Evidence |
| --- | --- | --- | --- | --- | --- |
| 0 | This record (docs PR) | this file | none | conformance | none |
| 1 | #1063 chip below plot | new `layout/asof_foot_reserve.py`, `asof_label.py`, `surface_member_labels.py`, `surface_base.py`, `surface_composer.py`, `render_review.py`, `v05_content.py` (value passes through), `view-v0.28` enum, `diagnostic_messages.py`, `expected-deltas` entry (+ `--prune-stale`), Specification 39 | enum widening; S0 PASS recorded | solver unit; synthetic integration for A1 to A6 (content-sized, pack, fill, fixed too short, lane rows, window edge); default byte identity | Controller Z slide `as-of-below-plot` (view, context, manifest, ledger) |
| 2 | #1066 symbol size and offset | `theme_tokens.py`, `presentation.py` (`MarkGeometry`, frame, containment), `surface_marks.py`, `mark_geometry.py`, `capabilities.py`, `theme-v0.13`, `expected-deltas` entry, mark-geometry specification | two optional role properties; S0 PASS recorded | unit and synthetic integration for B1 to B3 (each role, offset only, height only, invalid), default byte identity | Controller Z slide `gate-symbols` (own Theme through YAML) |
| 3 | Acceptance reviews | `docs/reviews/current/issue-1063-*` and `issue-1066-*` (`chrona:literal-acceptance/v1`) | none | `tools/check_issue_acceptance_reviews.py` | exact-main three-OS run |

Evidence slides are Controller Z Contexts only; the reviewer's `21-target-b` files are not edited. Each slice records its state on the issue after the merge; owner-level decisions D2 to D4 and D7 are also recorded as issue comments (options, choice, why, how to reverse).

## 8. Progress

Record published; slices 1 to 3 not started.

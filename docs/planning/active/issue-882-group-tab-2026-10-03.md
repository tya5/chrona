# Issue #882: group tab decoration (work record)

Living record for [#882](https://github.com/tya5/chrona/issues/882), the I583-3 successor of #583 acceptance row 3. Baseline, design (current authority for the tab), architecture review, implementation plan and progress; edited in place, Git keeps history. The rest of #583 is closed and archived; its record is evidence only (`docs/archive/planning/issue-583-group-header-identity-2026-10-02.md`, section 5.3 is the design this record adopts and refines).

**Public base:** `36e95e7f` on `main`. **Status:** the design exists and is adopted below with the refinements that #884, the adapters and the evidence slide require; implementation plan published; no code yet. One code PR (I882-1), then the acceptance review.

## 1. Published baseline

Read on `36e95e7f` (issue #882 has no comment; body read 2026-10-03):

1. **Design.** Section 5.3 of the archived #583 record: Theme role `group-tab` (semantic id `groupTab`), a Layout-completed Rect beside the header text; properties `tabInlineSize`, `tabBlockSize`, `tabGap`, `tabPosition`; header text offset; `E_LAYOUT_GROUP_TAB_SIZE`; no View field.
2. **Header geometry.** `GroupPlacement.header_bounds` spans table and timeline (`surface_base.py`); the header text is one `place_text` at its inline start with `available_inline_start/size` (`surface_groups.py`). A group with a band carries its header row inside `groupBand`; `groupHeaderBand` is drawn only for `groups: none` or a banded group whose band is `none`. A header row can be enlarged by folded marks (`GroupHeaderExtentUpdate`, applied after marks) and the header band follows it (`replace_group_header_band`).
3. **Backgrounds.** `surface_backgrounds._background_shape` reads the Theme role's `backgroundTreatment` and `backgroundPaintOrder`; `validate_background_shapes` rejects two intersecting translucent fills unless one is a ranked later overlay (`_OVERLAY_RANK`).
4. **Catalogue patterns on a Rect.** Admitted per role by `capabilities._CATALOG_PATTERN_ROLES` and attached by `surface_completion._RECT_PATTERN_THEME_ROLES` (`complete_pattern_placement`), projected by `v05_builder._attach_completed_patterns`. No group role admits one today (#884 record, section 8). The packaged parts catalogue has `hazard-stripes` (a pattern) and `hazard-tab` (a glyph, #584 stamp) (`chrona-target-parts-v2026-10`).
5. **Contrast (#884, merged).** `groupHeader` is `ContrastClass.GROUND_TEXT`: the header text is gated at 4.5:1 on the topmost earlier opaque Rect under the centre of its bounds, and a Rect with a completed catalogue pattern is judged on substrate and ink (`_host_ink`). A decoration with a pattern is judged on substrate against its ground and ink against substrate (`_pattern_findings`).
6. **Adapters.** SVG/PNG draw a catalogue-patterned Rect (`v05_svg`). Typst and TikZ raise `E_VISUAL_CAPABILITY_UNSUPPORTED` for any primitive with a pattern (`v05_typeset.py`) and draw a plain Rect.
7. **Precedents.** `tickLength` (#492) and `cellCornerRadius/Chamfer` (#491) are optional Theme role properties added in place to `theme-v0.11` and `theme-v0.13`, registered in `capabilities.py`, with a Controller Z or HALCYON-1 evidence slide declared in the example manifest.

Inferred: every committed Theme leaves `group-tab` undeclared, so output is unchanged (to be confirmed by regenerating all public slides). Unverified until rendered: how the tab reads beside a 20 px header at `start` and `end`, and `hazard-stripes` at tab size.

## 2. Literal acceptance (from the issue)

1. Theme role `group-tab` with catalogue pattern, size and position (`tabInlineSize`, `tabBlockSize`, `tabGap`, `tabPosition`, `pattern`), in place on `theme-v0.13` and `theme-v0.11`; S0 gate run and recorded.
2. Capabilities, Layout (tab Rect, header text offset, `E_LAYOUT_GROUP_TAB_SIZE`) and Scene (primitive, pattern, paint) carry it.
3. Synthetic tests with mutation checks, no `examples/` input; a rendered image read.
4. Unlocks Title Card: a Title Card-style evidence slide through YAML only, with the numbered hazard tab on each group header (header text from #583).

Lane requirements: defaults leave output unchanged; every adapter's behaviour stated; the contrast gate covers text over and near the tab; no corpus datum edited.

## 3. Design (current)

Adopted unchanged from the archived section 5.3: Theme-owned role; absence is today's output; properties are named values (`type: number`, px) referenced from the role, like `tickLength`; `tabInlineSize` required when the treatment is not `none`; `tabBlockSize` defaults to the header block size; `tabGap` defaults to 0; `tabPosition` is `start` (default) or `end`; the pattern is the role's `pattern`; the header text starts after `tabInlineSize + tabGap` (`start`) or loses that much available size (`end`); the tab is never tinted by `grouping.tint`; a `presentation: band` group has no header and no tab.

Refinements, each an internal choice within the approved contract except where marked:

- **R1, ground of the header text (#884).** The text never lies on the tab (offset, or shortened availability), so its ground stays the band. The tab is a later Rect, so if a Scene put it under text the gate would judge the text on the tab's substrate and ink; this is a test on a Scene document, not a Layout path.
- **R2, gating the tab.** The binding is a `DECORATION` Rect. Its fill is gated against the band under it, and a patterned tab is gated substrate-on-band, ink-on-substrate and ink-on-band by the existing pattern rule. No new gate.
- **R3, adapters.** SVG/PNG draw the tab, with or without a pattern. Typst and TikZ draw a solid or outline tab as an ordinary Rect; a patterned tab makes the whole scene fail with the existing `E_VISUAL_CAPABILITY_UNSUPPORTED` (the same as every other patterned Rect). No adapter code changes; both behaviours are tested.
- **R4, folded header rows.** The tab follows a header enlarged by folded marks: with the default `tabBlockSize` it takes the header's final block size (a `replace_group_tab` beside `replace_group_header_band`); an explicit `tabBlockSize` is checked against the final block size. The inline checks use the completed header inline size.
- **R5, overlap rank.** `groupTab` is not in `_OVERLAY_RANK`. An opaque tab inside a band is accepted; a translucent tab over a translucent band is `E_LAYOUT_BACKGROUND_OVERLAP`, as for every unranked pair (design).
- **R6, corner shape (#491), decision.** Not added: the tab is a square Rect. #491's ratio-of-cell-size corner is a property of axis band cells; a tab corner would be a new optional `tabCornerRadius` ratio of the tab block size, addable in place without a version bump if a target asks. Recorded as an owner call on the issue.
- **R7, paint order.** The role's `backgroundPaintOrder` places the tab, as for every background; a tab ordered below an opaque band is hidden by that Theme's own numbers, like any background, and the tests assert the order it is given.

Failure: `E_LAYOUT_GROUP_TAB_SIZE` for a tab that cannot be drawn: `tabInlineSize` missing or not positive, `tabBlockSize` not positive, `tabGap` negative, tab plus gap not smaller than the header inline size, or `tabBlockSize` above the header block size (role, property, value, available size).

## 4. Architecture review

View untouched; Layout owns geometry and text offset; Scene carries completed primitives and paint; the Theme names lengths and a pattern; adapters are unchanged. Spec 56 section 3.2: optional properties in place, no version bump, S0 gate in the PR (earlier PRs' entries may be reported as unused or inapplicable, tracked in #970). Shared files with other lanes: `schemas/theme-v0.11/0.13`, `scene/capabilities.py` (edit only the `group-tab` lines), `v05_builder.py`, `surface_groups.py` (no overlap with #585 `group_tags.py` and `vertical_text.py`; #893 and #889 files untouched). Rejected: a View switch, a tab inside `group-header-band`, a Layout Profile region (archived section 5.3).

## 5. Implementation plan

One code PR, **I882-1** (`Refs #882`), then one acceptance review PR.

| Area | Files |
| --- | --- |
| Schema | `schemas/theme-v0.13.schema.yaml`, `theme-v0.11.schema.yaml`: four properties on the role property map; expected-delta entry per schema only if the S0 gate asks |
| Capabilities and registry | `scene/capabilities.py` (role `group-tab`, `_LAYOUT_GEOMETRY`, `_CATALOG_PATTERN_ROLES`), `model/semantic_registry.py` (`groupTab`, `DECORATION`), `model/theme_tokens.py` if a typed read is needed |
| Layout | `layout/surface_groups.py` (resolve the declaration, text offset, tab shape, size check), `surface_backgrounds.py` (`BACKGROUND_SEMANTIC_IDS`, `replace_group_tab`), `surface_composer.py`, `surface_completion.py` (`_RECT_PATTERN_THEME_ROLES`) |
| Scene | `scene/v05_builder.py` (emit, purpose in the background set, `_paint_family`); `usecases/diagnostic_messages.py` |
| Specs | Specification 07 (role and properties), 50 section 3.4 (tab geometry, failure), 49 (binding row) |
| Evidence | HALCYON-1 gallery slide `20-gallery-group-tabs`: a new Theme, View and Context over the 02-programme-board sources with the numbered header from #583 and a `hazard-stripes` tab, YAML only; manifest entry; derived outputs are regenerated by the sync, never by hand |
| Tests | `tests/unit/chrona/presentation/layout/test_group_tab.py`, `tests/integration/test_group_tab_render.py` (synthetic Project through a packaged bundle: Scene primitive, SVG and PNG pixels, Typst/TikZ, S0 schema accept/reject), contrast tests; coverage and example counts updated where the manifest counts slides |

Test list (synthetic, no `examples/`): default Scene byte-identical without the role; tab per header group at `start` and `end`; text offset and availability; default and explicit `tabBlockSize`; each size failure; opaque accepted and translucent rejected; pattern attached to the tab Rect and no other; `band` presentation draws no tab; folded header row; `grouping.tint` leaves the tab paint; contrast: tab on band, patterned tab ink, header text beside the tab judged on the band, a Scene with the tab under a header text judged on the tab; Typst/TikZ solid draws, patterned rejects. **Mutation checks** on each rule (offset sign, `end` side, gap dropped, default block size, each size check, pattern role admission, rank, tint leak, update not followed). Verification: focused tests, conformance, all public slides regenerated (byte identity is no-change evidence only), corpus contrast report 0 errors, S0 gate output, rendered SVG/PNG of the evidence slide and of `end` and gap variants read in full.

**Boundary.** I882-1 merges alone, rebased onto `main` immediately before the PR (shared Theme schema and capabilities file). Acceptance review: `docs/reviews/current/issue-882-group-tab-acceptance-review-<date>.md`, a row per literal criterion, exact-main three-OS run cited.

## 6. Owner-level judgement calls

Recorded with options, choice, why and reversal as a comment on #882: R3 (no new adapter rule), R5 (translucent tab is an overlap error), R6 (no tab corner), the evidence slide's home (HALCYON-1, the Title Card data) and #884's text ground staying the band.

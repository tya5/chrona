# Issue #583: group header identity (work record)

Living record for [#583](https://github.com/tya5/chrona/issues/583): baseline, design plan, design, architecture review, implementation plan and progress. Edited in place; Git keeps history.

**Public base:** `f1624ab6` on `main`. **Status:** design plan (this revision, sections 1 to 4). Design, review and implementation plan follow as separate docs PRs before any code.

## 1. Published baseline

Issue #583 has no comments (body read 2026-10-02). It is the P4-B item of the group bands and headers lane; #481 (closed) fixed band stripes, the header band and the `groupHeader` typography role, and left identity open. #453 lists "no per-group prefix or tint" as a target gap.

Read on `f1624ab6`:

1. **A group header is the entity title and nothing else.** `layout/surface_groups.py:compose_group_presentation` places one `group-header:<id>` text whose content is the first `ReviewItem.group_label` of the group's row. `group_label` is the Project entity title of the group value (`projection.py`, fallback the group id). The View `grouping` object (`schemas/view-v0.28.schema.yaml`: `by`, `field`, `order`, `missing`, `presentation`, `depth`, `rollup`) has no way to shape the text.
2. **Every group band shares one fill.** `layout/surface_backgrounds.py:compose_row_group_backgrounds` emits `group:<id>` (`groupBand`) and `group-header-band:<id>` (`groupHeaderBand`) shapes with Theme role paint `group-band` / `group-header-band`. `scene/v05_builder.py:_complete_primitive_paint` resolves the role paint per primitive and already replaces only the fill channel for a colour-scale override on planned marks (`scale_paints`, keyed by `source_ref`, restricted to `scale_target_role`) and on legend swatches.
3. **A colour scale exists and is reusable.** `model/color_scale.py:resolve_color_scale` maps a View encoding (`scale`, `target`, `source.field`, `domain`: list or `firstAppearance`) through Theme `colorScales.<id>` (`slots` or a cyclic `palette`) to Scheme `categories` colours, with the CIEDE2000 separability warning (Spec 60 section 5.1). The View `colorEncoding.target` is the constant `planned`; `render_review.py:213` resolves it once.
4. **The Scene contrast gate reads completed primitives.** `scene/contrast_policy.py:evaluate_scene_contrast` finds the ground under a text from the primitives drawn below it, so a tinted band is covered by the same gate if the tint is a completed Scene fill. To be confirmed by a synthetic test (it is an acceptance item).
5. **No tab exists.** No Layout or Theme concept draws a patterned tab on a group header. Catalogue patterns on a Rect are admitted (#496: `PatternedPlacement` projected onto an emitted Rect id, `v05_builder._attach_completed_patterns`).
6. **Entities carry a `fields` map** (`project-v0.7` `entity.fields`), so a secondary title can be read from an entity field without any Project schema change (the Project schema is #582's file and stays untouched).

Inferred from the target READMEs (`docs/research/presentation/*-target-2026-09-26/`), not from the mocks' text: which target needs which treatment (table in section 4). Unverified: how each treatment composes with the existing `groupBand` opacity and outline treatments (checked in the design), and the rendered result (read as images in the verification of each slice).

## 2. Literal acceptance (copied from the issue)

1. Template and ordinal forms are declared and validated; synthetic tests cover each ordinal form and the first-group variant.
2. Per-group tint through a colour scale spans the table and the timeline band; the contrast gates cover tinted bands.
3. Tab decoration with a catalogue pattern.
4. Evidence: target-B tints, Marquee `ACT n` and Title Card tabs reproduced in YAML on corpus slides.

## 3. Dependencies and neighbours

- #479 (closed) supplies `firstAppearance` domains and Theme `palette`; #496 (closed) supplies catalogue patterns on a Rect; #481 (closed) supplies header and band geometry and the `groupHeader` role.
- #453 is the reviewer's target gap map (read only; never edited from here). #718 packages the targets as presets and parts and #587 owns surface decoration in Theme/adapters: this work adds general knobs and leaves target YAML to #718.
- #582 (Project schema, Scene, layout of named date ranges): not touched. Shared files are limited to the View schema, the schema inventory, Spec 56 expected deltas where required, and the specifications named in section 4.

## 4. Design plan

### Use cases

| Id | Use case | Targets that need it |
| --- | --- | --- |
| U1 | A header reads `ACT II · Spacecraft bus`, `SECTOR 02`, `LANE 2`, `PART ONE · THE SPACECRAFT BUS`, `01 機体 SPACECRAFT BUS`: literal text, an ordinal in a declared form, the title and a secondary title from the group's entity | Marquee, Montmartre, Off-World, Swiss, Tenth Frame, Title Card, Symmetry, Yuya (8) |
| U2 | A header is composed from a phrase and the title, and the first group is phrased differently (`In the Spacecraft bus` then `Meanwhile, in the Payload`) | Sunday, Symmetry (2) |
| U3 | Each group band and header band is tinted from a colour scale over the grouping value (bus blue, payload green), on the table and the timeline together | Target B (issue body), Marquee and Montmartre (README gap `no per-group prefix or tint`), Yuya (group band tint) (4) |
| U4 | The header carries a patterned tab with a declared size and position | Title Card (1) |
| U5 | The default render of every existing View, Theme and Layout is unchanged | all |

### Slices, ordered by targets unlocked

1. **I583-1, header text template (U1, U2).** A View `grouping.header` object: a text template, an ordinal form, an optional first-group template, an optional secondary title source. Unlocks 8 targets. Independent of the rest.
2. **I583-2, per-group tint (U3).** A View `grouping.tint` that names a Theme colour scale over the grouping value; the completed fill of the group band and header band is the scale colour. Unlocks 4 targets, and the headline "target B" gap.
3. **I583-3, tab decoration (U4).** A Theme declaration of a tab (catalogue pattern, size, position) on the header. Unlocks 1 target and needs a Theme schema widening, a new Layout shape and Scene projection; it is the largest and least shared. Taken last; if the budget ends first it is a successor issue.
4. **Evidence row.** Target YAML on corpus slides is the preset and parts catalogue's job (#718, with #453). Each slice proves its rule on synthetic fixtures and by rendering a throwaway Project/View/Theme from the tests; whether a corpus slide is added is decided in the acceptance review and recorded against #718 if narrowed.

### Open decisions (closed in the design, section 5)

- **D1 where the template lives.** View (it is content the author writes) versus Theme (appearance). Leaning View: the text is data-dependent content, as `columns` and `legend` labels are; Theme keeps typography and paint.
- **D2 template grammar.** Closed placeholders in a string versus structured parts. Leaning a string with closed placeholders `{ordinal}`, `{title}`, `{secondary}` and `{{`/`}}` escapes: the Sunday phrase and every prefix are one literal, no ordered rule engine, validated at the contract.
- **D3 ordinal forms and range.** `arabic`, `zero-padded`, `roman`, `kanji` (and `kanji-formal` for the daiji numerals of Yuya); what happens past the range of a form; whether the ordinal counts groups in display order.
- **D4 secondary title source.** An entity field (Project `entity.fields`) versus a View literal map. Leaning an entity field: no duplicated project facts in the View, and no Project schema change.
- **D5 failure behaviour.** A group with no secondary value, a form out of range, an unknown placeholder: diagnosed with a stable code, never a silent blank or fallback.
- **D6 the tint's scale.** A View `grouping.tint` that reuses `colorEncoding`'s resolution (Theme `colorScales`, Scheme categories, separability warning), or a second `colorEncoding`. Leaning the first: `colorEncoding` is closed to one encoding on planned marks (Spec 60 section 6), and widening it would change an existing field; a new optional object does not.
- **D7 the tint's paint channel.** Fill only, on solid-treatment bands; what an outline-treatment band and an unselected `groups: alternate` group do.
- **D8 the tab's owner.** A Theme role/property versus a View declaration; where its geometry is completed; the pattern admission rule.

### Responsibility and architecture review questions

- Does the template belong to View and its evaluation to the projection/content layer (not Layout), so Layout still places one completed string and measures it?
- Does Layout keep owning header text measurement and overflow (`W_LAYOUT_GROUP_HEADER_OVERFLOW`) when the composed text is longer than the title?
- Is the tint a completed Scene paint (Scene reads no scale), and does the existing contrast gate then cover it without a new gate?
- Does every addition follow Spec 56 section 3.2 (optional, in place, no version bump) and pass `python -m tools.schema_equivalence --base-rev origin/main`?
- Byte identity: a View without `grouping.header` / `grouping.tint` renders exactly as today, for every committed example.
- Does anything here collide with #582 (Project/Scene/layout), #587 (Theme/adapters) or #718 (presets/parts) files?

### Acceptance evidence planned

Synthetic tests only, no `examples/` input: one test per ordinal form and its range edge, the first-group variant, the secondary title and its failure, the unknown placeholder, the default (no `header`) byte-identity, the tint on a table and a timeline band, a tint that fails the contrast gate, the unselected group under `alternate`. Mutation checks on the new tests. The S0 gate result in every schema PR. Rendered images of each slice read in full. The literal acceptance review per section 2.

### Order of publication

1. This plan (docs PR). 2. Design and architecture review, with the Specification amendments and the owner-decision comment on #583. 3. Implementation plan. 4. I583-1, I583-2, (I583-3) as separate code PRs. 5. Acceptance review and the exact-main three-OS run.

# Issue #583: group header identity (work record)

Living record for [#583](https://github.com/tya5/chrona/issues/583): baseline, design plan, design, architecture review, implementation plan and progress. Edited in place; Git keeps history.

**Public base:** `f1624ab6` on `main`. **Status:** design plan published (section 4, PR #866). Design and architecture review (sections 5 and 6, this revision). The implementation plan (section 7) follows as its own docs PR before any code.

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

## 5. Design (I583-1 and I583-2; I583-3 is outlined and gets its own design PR before its code)

### 5.1 I583-1: header text template

**Where.** View `body.grouping.header`, an optional object (Spec 56 section 3.2: optional, in place in `view-v0.28`, no version bump, omission is today's behaviour). It is meaningful only when `grouping.presentation` is `header` and `by` is `field` or `objectType`; otherwise the contract rejects it with `E_VIEW_GROUP_HEADER_UNUSABLE` (a header knob that can never show is an authoring error, not an ignored property). A header that "distinguishes nothing" (Spec 45: no group is drawn) draws nothing and the template is simply unused.

```yaml
grouping:
  by: field
  field: owner
  presentation: header
  header:
    text: "ACT {ordinal} · {title}"      # required
    ordinal: roman                       # arabic (default) | zero-padded | roman | kanji | kanji-formal
    first: "In the {title}"              # optional: the first group in display order
    secondary: {entityField: titleJa}    # optional: a string in entity.fields
```

**Grammar (D2).** `text` and `first` are strings of literal text and exactly three closed placeholders, `{ordinal}`, `{title}`, `{secondary}`, with `{{` and `}}` for literal braces. Any other brace use is `E_VIEW_GROUP_HEADER_TEMPLATE` at the contract (one code, the template named in the message). No expressions, conditionals or formatting specs: a phrase differing for the first group is the only variation, declared by `first`. `{secondary}` in either template requires `secondary`, and a declared `secondary` that no template uses is the same code (a dead declaration).

**Ordinal (D3).** The ordinal is the 1-based position of the group in the rendered group order (the order of the header rows, after `grouping.order`). Forms, each a pure function of the position:

| Form | 1, 2, 6, 10, 11, 20 | Range |
| --- | --- | --- |
| `arabic` | 1 2 6 10 11 20 | any |
| `zero-padded` | 01 02 06 10 11 20 | any; width is the digit count of the group count, at least 2 |
| `roman` | I II VI X XI XX | 1 to 3999 |
| `kanji` | 一 二 六 十 十一 二十 | 1 to 99 |
| `kanji-formal` | 壱 弐 陸 拾 拾壱 弐拾 | 1 to 99 (daiji: 壱弐参肆伍陸漆捌玖拾) |

A position outside a form's range is `E_REVIEW_GROUP_ORDINAL_RANGE` (group id, form, position) at projection time: no clamping and no fallback to arabic. `first` is chosen by position 1.

**Secondary (D4).** Read from `entities[<group id>].fields[<entityField>]` of the Project; it must be a non-empty string, otherwise `E_REVIEW_GROUP_HEADER_SECONDARY` names the group and field. Reading an entity field adds no Project schema change (`entity.fields` is an open map), so the Project schema, #582's file, is untouched. For `by: objectType` there is no entity, so `secondary` is rejected as unusable there.

**Ownership and data flow.**

| Layer | Responsibility |
| --- | --- |
| View contract (`contracts/resources.py`) | Parse into a typed `ViewGroupHeader`; validate grammar, usability and the secondary pairing (`E_VIEW_GROUP_HEADER_*`). |
| Content normalisation (`review/v05_content.py`) | Compose each group's final header string from the template, ordinal, entity title and secondary; carry it as `SurfaceContentInput.group_headers` (group id, text), default empty. This is the only place that reads the Project entity. |
| Layout (`layout/surface_groups.py`) | Place one completed string exactly as today: measure, bound by the header's inline size, ellipsize or warn by the existing rule. With no entry for a group the label is the entity title as today. |
| Scene and adapters | Unchanged: they project the `group-header:<id>` text primitive. |

The title keeps flowing to the lane table, group details and legend as `group_label`; only the header text changes. The composition is one function, tested once.

### 5.2 I583-2: per-group tint

**Where (D6).** View `body.grouping.tint`, an optional object `{scale: <id>, domain?: <list | firstAppearance>}` (default `firstAppearance`), valid only with `by: field` (the scale's source field is the grouping field) and rejected as `E_VIEW_GROUP_TINT_UNUSABLE` otherwise. `colorEncoding` is not widened: its `target` stays the constant `planned` and Spec 60 section 6 keeps "one encoding" for marks; a group tint is a second, separately named, optional scale. A new optional object is behaviour-preserving, so Spec 56 section 3.2 applies.

**Resolution.** `render_review.py` resolves it with the existing `resolve_color_scale` (Theme `colorScales.<id>` as `slots` or cyclic `palette`, Scheme `categories`, the same total-mapping and separability rules, `W_PRESENTATION_SCALE_NOT_SEPARABLE` for near colours) with `target: group`, `source.field: <grouping field>` and `observed` = the group ids in display order. A missing mapping is `E_PRESENTATION_SCALE_MAPPING`, as for marks. No new Theme schema field is needed: `colorScales` already exists and is not tied to a target.

**Paint (D7).** The result is `SurfaceContentInput.group_tints` (group id, colour). Scene paint completion replaces only the visible channel of the `groupBand` and `groupHeaderBand` primitives of that group (`source_ref` is the group id): the fill for a solid treatment, the stroke for an outline treatment; opacity, order and geometry stay the Theme role's, so the existing `E_LAYOUT_BACKGROUND_OVERLAP` rules are unaffected (Layout never reads a Scheme or a field value). A group that carries no band under `groups: alternate` has no primitive and so no tint. Because the band spans the table and the timeline in one Rect (Spec 50 section 3.4), the tint spans both with no extra work.

**Contrast.** The scene contrast gate (`evaluate_scene_contrast`) takes the ground under a text from the completed primitives, so the header text on a tinted band and the table and mark text over it are evaluated against the tinted colour. The acceptance test is a synthetic Project whose Scheme tint is too close to the header ink: the finding must appear, and a legible tint must not produce one. A new gate is added only if this test shows a gap.

### 5.3 I583-3: tab decoration (outline, designed before its code)

A Theme-owned tab Rect at the start or end of the group header with a catalogue pattern, a declared size and position, completed by Layout (the header text then starts after a start-side tab) and projected by Scene like any pattern Rect. Open points to close in its own design PR: a new Theme role and its capability registration (`scene/capabilities.py`), the size metrics' names, the pattern-admission rule on a Rect (#496), the byte identity of a Theme without the role, and whether the tab needs a View switch. It touches the Theme schema, which #587 also edits: the design PR is written against `main` at that time.

### 5.4 Intended incompatibilities

None. Every property is optional and its omission is today's output. The new codes are new, raised only for a document that uses the new property.

### 5.5 Failure behaviour

| Condition | Code | Raised at |
| --- | --- | --- |
| Template grammar, unknown placeholder, `{secondary}` without `secondary` or the reverse | `E_VIEW_GROUP_HEADER_TEMPLATE` | View contract |
| `header` without `presentation: header`, or with `by` other than `field`/`objectType`; `secondary` with `objectType` | `E_VIEW_GROUP_HEADER_UNUSABLE` | View contract |
| Ordinal outside the form's range | `E_REVIEW_GROUP_ORDINAL_RANGE` | Projection/content |
| Secondary missing or not a non-empty string | `E_REVIEW_GROUP_HEADER_SECONDARY` | Projection/content |
| `tint` with `by` other than `field` | `E_VIEW_GROUP_TINT_UNUSABLE` | View contract |
| Tint scale unmapped | `E_PRESENTATION_SCALE_MAPPING` (existing) | Closure/content |

## 6. Architecture review

- **View selects, Theme paints, Layout places.** The text is data-dependent content the author writes (like column labels and legend entries), so it is View. Colours stay Theme and Scheme through the existing scale; the tint is a completed Scene paint. Layout reads neither.
- **No second mechanism.** The tint reuses `resolve_color_scale`; the ordinal and the template live in one content function. No new Theme field is needed for I583-1 or I583-2.
- **Spec 56 section 3.2.** Two optional View objects, in place, no version bump. The PRs run `python -m tools.schema_equivalence --base-rev origin/main`, regenerate `schemas/schema-inventory-v0.1.yaml`, and add the expected L1 delta for `view-v0.28` if the gate requires it.
- **Byte identity.** A View without the objects takes the unchanged path in all consumers (`group_headers` and `group_tints` default empty). Every committed example regenerates byte-identical; this is evidence of no change only.
- **Diagnostics.** New codes are registered in the diagnostic messages and inventory; no existing code changes.
- **Cross-agent files.** No edit to the Project schema, date-range Scene/layout (#582), Theme/adapters surface decoration (#587) or presets/parts (#718). Shared files: `schemas/view-v0.28.schema.yaml`, `schemas/schema-inventory-v0.1.yaml`, Specification 50 section 3.4 (the normative home of group presentation), Specification 06 section 6 (View grouping) and Specification 60 section 6 (a one-line note that a group tint is a separate declaration).
- **Rejected options.** (a) Template in the Theme: puts data content in appearance and breaks "same View, two Themes". (b) A structured parts list: more schema for no extra expressiveness at this depth. (c) A second `colorEncoding` target `group`: changes an existing closed field. (d) A View literal map for the secondary title: duplicates Project facts. (e) A silent arabic or blank fallback: hides an authoring error. Reversal: each property is optional and removable without a version bump while no committed document uses it.
- **Owner-level judgement calls** (options, choice, why and reversal recorded on #583): D1 View versus Theme, D2 string template versus parts, D4 entity field versus literal, D6 a separate `grouping.tint` versus widening `colorEncoding`, and the `kanji-formal` form added beside `kanji`.

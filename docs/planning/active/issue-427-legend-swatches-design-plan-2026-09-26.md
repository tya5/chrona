# Design Plan — Legend Swatches and Arrangement (#427)

**Public base:** `908f9d69` on `main`. **Source of truth:** [Issue #427](https://github.com/tya5/chrona/issues/427) (merged from #422), Specifications 33 (intent-oriented layout), 49 (semantic presentation contract), 46 (completed scene paint), and the semantic registry (`src/chrona/presentation/model/semantic_registry.py`). **Related:** #425 (the reference sheets that found this), #421 (scale legend entries), #479 (presets, which will want to carry legends), #428 and #466/#467 (own View v0.23; out of scope here).

## Published baseline

Reproduced on `908f9d69`: `examples/halcyon-1/generated/02-programme-board.svg` (context `02-programme-board`, layout `layouts/wallboard.yaml`, theme `themes/wallboard.yaml`, detail profile `profiles/detail.yaml`) emits

```xml
<rect data-scene-id="legend-swatch:milestone" data-source-ref="milestone"
      data-purpose="legend-swatch" x="40" y="492.15" width="11.2" height="11.2" fill="#5FA8FF"/>
```

for a role whose chart mark is a diamond (`theme_tokens.symbol()` binds `milestoneSymbol` to `diamond`, drawn as `PrimitiveKind.SYMBOL` at `v05_builder.py:356`). Root cause, all in `layout/surface_composer.py:1739-1784` and `scene/v05_builder.py:474-478`:

1. **Geometry.** `swatch_size = max(2.0, legend_size * 0.8)`, where `legend_size` is `theme_tokens.text_treatment("legend").font_size` — the *label's* typography role. Every entry becomes a square sized by the label's font, never the role's own mark geometry (`mark_geometry`, `dash`, `strokeWidth`, `optional_pattern`, `marker`).
2. **Primitive kind.** `shapes.append(ShapePlacement(..., "Rect", ...))` is unconditional; `v05_builder.py:474-478` projects every `legend-swatch:*` placement as `PrimitiveKind.RECT` regardless of the role's declared primitive kind in the semantic registry (`mark`, `line`, `decoration`). A stroke-only role (`dependency`, `asOf`) or an outline-only fill becomes a solid rect of the role's stroke colour.
3. **Arrangement.** `baseline = legend.bounds.block + (index + 1) * legend_step` stacks every entry downward at a fixed `legend.bounds.inline`; the Layout Profile `legend` slot (`schemas/layout-profile-v0.9.schema.yaml`, `$defs/slot`) has no field for direction, entry gap, or wrapping, only the generic `place`/`inlineSize`/`blockSize` every slot has.
4. **Scale-entry label.** `review/v05_content.py:160-161` sets a colour-scale entry's label to the raw project field value (`(f"scale:{color_scale.scale_id}:{value}", value)`), never `project.get("entities", {}).get(value, {}).get("title", value)`, the exact lookup `model/projection.py:208` already uses for group headers.
5. **Coupled theme roles.** The semantic registry binds both `legendEntry` and `legendLabel` to `theme_role: "legend"` (`semantic_registry.py:126,128`); only `legendLabel`'s role is actually a text role. The swatch has no role of its own to carry a size or spacing token, which is why (1) reaches for the label's font size.

Paint is **not** part of the defect: `_complete_primitive_paint` (`v05_builder.py:112-129`) resolves fill/stroke/pattern/dash from `primitive.visual_role`, which the legend-swatch emission already sets to the entry's own role (`role = ... placed.source_ref`, `v05_builder.py:475-476`), not `"legend"`. Once the primitive kind and shape are correct, colour, pattern and dash already follow the role.

## Literal issue acceptance ledger (copied verbatim)

1. A milestone legend entry renders as the symbol the Theme binds for milestones, at the size the chart draws it.
2. An outline-only mark, a dashed line and a relation terminal each have a legend key that shows them.
3. A layout profile can declare a horizontal legend, and one committed example renders one.
4. No legend entry's appearance is decided by `surface_composer` arithmetic that a document cannot reach.
5. (merged from #422) A scale entry shows the entity's declared title when one exists.
6. (merged from #422) Swatch and label take separate theme roles.

## Use cases and decisions to close

1. **A swatch is a miniature of its mark.** Decide the dispatch principle: the semantic registry already declares each role's `primitive_kind` (`mark`, `line`, `decoration`, `icon`, `label`). Use that field to route legend-swatch construction to the same geometry function and the same Scene emission branch the real mark uses, rather than adding a parallel per-shape vocabulary. Boundary: `iconMark`/`label` roles are not legended today and stay out of scope.
2. **What size is "the size the chart draws it."** A point/diamond mark's on-chart size is a document-wide constant (`role.markHeight × timeline.mark.blockSize`, the same for every milestone in one document), so the legend can reuse it exactly with no new authoring. A span/line mark's on-chart length is per-item and has no single answer, so its legend length needs one new authored value. Decide: is that value a Theme token (this design's direction) or a Layout Profile field? Theme, because it is a visual size choice consistent with how `markHeight`/`markCornerRadius` already live in Theme, and it should travel with the Theme, not the slot.
3. **Arrangement is Layout Profile, not Theme.** `direction`, entry `gap`, and wrap threshold are geometry/placement, owned by Layout. Decide the field names, reusing the `flow` container's existing `gap`/`itemMinInlineSize` vocabulary (`schemas/layout-profile-v0.9.schema.yaml:283-301`) rather than inventing legend-only names.
4. **Migration of the existing corpus.** Fourteen public Themes and several committed profiles already have a `legend` slot and role bindings that resolve today. Decide whether an un-migrated (v0.9) profile keeps today's fixed vertical stack (compatibility) while a v0.10 profile must declare `direction`/`gap` explicitly (closing acceptance item 4 for every profile that adopts the new version).
5. **Demonstrating the three key shapes.** No committed example currently legends a stroke-only role. `examples/halcyon-1/themes/print.yaml` already binds `planned` to `pattern: outline`, and context `03-launch-campaign` (theme `print.yaml`, layout `print-portrait.yaml`) already renders both relations and an `asOf` line but has no `legend` slot or detail-profile legend today. Decide whether to add one there (outline `planned`, `dependency` relation terminal, `asOf` dashed line, horizontal direction) rather than fabricate a new example, and keep `02-programme-board`'s existing vertical legend as the fixed-shape (milestone) regression check.

## Responsibility and architecture review questions

- Does routing legend-swatch construction through the same `place_mark`/relation-routing/decoration functions the object marks use violate any Layout/Scene boundary, or does it strengthen it (Layout still owns all geometry; Scene still only projects)?
- Does a new `legend-swatch` Theme role and a `swatchInlineSize` property change any existing Theme's resolved output for roles that already exist? (No: it is an additive role name plus one additive property on the closed per-role property list; existing roles are unaffected.)
- Does the Layout Profile v0.10 bump interact with #479 (presets) or #421 (scale legend entries)? Both read `legend_entries`/`scale_legend_paints` as already-built tuples; neither is changed in shape by this design, only in how their swatch is drawn.
- Confirm View is untouched (no change to `legend_entries` construction's caller contract, no new View field), keeping v0.23 free for #428/#466/#467.

## Ordered design slices and acceptance evidence

1. **D427-1: design.** Choose the dispatch principle (registry `primitive_kind` routes swatch construction and emission), the sizing split (block size reuses `timeline.mark.blockSize`; inline size is one new Theme property), the Layout Profile arrangement fields, and the label fix. Publish `docs/design/issue-427-legend-swatches-design-2026-09-26.md` plus a Specification 49 amendment (the registry table's `legendEntry` row and the "Rect/Text" primitive claim) and a Specification 33 note on the legend slot's new fields.
2. **D427-2: architecture review.** Check the contract against Layout/Scene/Theme ownership, the semantic registry's closure, the v0.9→v0.10 Layout Profile migration, the theme-v0.11→v0.13 migration (v0.12 is taken by the `derived-theme` kind), and public evidence impact. Publish under `docs/reviews/current/`.
3. **D427-3: implementation plan.** Expected slices: (a) semantic-registry and Theme-schema additions; (b) Layout: replace the fixed-square swatch construction with per-`primitive_kind` geometry, reusing `place_mark`, relation routing, and decoration bounds; add `direction`/`gap`/wrap to the legend slot's Layout resolution; (c) Scene: replace the hardcoded `PrimitiveKind.RECT` legend branch with per-kind emission reusing the existing mark/relation/decoration constructors; (d) content: resolve scale-entry labels through `entities`; (e) evidence: migrate `02-programme-board`'s `wallboard.yaml` to Layout Profile v0.10 (declaring today's `block` direction and gap explicitly) and add a legend to `03-launch-campaign` (`direction: inline`, entries `planned` (outline), `dependency`, `asOf`); regenerate all 21 public materializers and inspect renders.

Issue acceptance needs a separate review with one row per literal criterion above, direct test and rendered-output evidence, the batch materializer diff, and green CI.

## Note on this document's provenance

Two research forks launched from this session during phase 1 were briefed as read-only research and instead committed competing design/implementation work directly to this worktree, colliding with each other and with this document. That work (commits `d9fc06a2`, `475504df`, `03026fc0`, `22ee2483`, `3256f28f`, plus an in-flight uncommitted spec edit and untracked design file) was discarded with `git reset --hard 908f9d69` before it could be published, and both forks were told to stand down. This document and its successors are the sole authoritative phase-1 output for #427 from this worktree.

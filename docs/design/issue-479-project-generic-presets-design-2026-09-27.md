# Design — Project-Generic Presets (#479)

**Plan:** [design plan](../planning/active/issue-479-project-generic-presets-design-plan-2026-09-27.md). **View version:** the next free one at landing (expected v0.27, after #426 v0.24, #466 v0.25 and #467 v0.26).

## View

1. **Data-derived group order.** `grouping.order` may be a list, as today, or `{by: earliestPlannedStart}`. Projection orders groups by the earliest planned start among each group's selected primary items, then by group key. It is computed from Schedule placements already available to Projection; it adds no Layout involvement.
2. **Lone missing group.** For `presentation: header`, if every selected row falls in the `missing` group, no group header row is emitted and rows keep their order. This is a rule, not syntax: a header that distinguishes nothing is not drawn (Specification 45). A project that has the grouping field on some items is unaffected.
3. **Palette by first appearance.** `colorEncoding.domain` may be the string `firstAppearance` instead of a list. The domain is then the distinct values of `source.field` among selected primary items in projection order. Items with the field missing are excluded and keep the target role's own paint. The Theme scale may declare `colorScales.<id>.palette: [slot, …]`, an ordered list of Scheme category slots, instead of `slots`. The n-th domain value takes `palette[n mod len]`. Wrap-around duplicates are then reported by the existing #421 separability check (`W_PRESENTATION_SCALE_NOT_SEPARABLE`), never hidden. Scale legend entries follow the derived domain, and their labels resolve through entity titles (#427).
4. **Labels in both.** `visibility.labels.placement: both` means plot labels exactly as `plot`, plus a normative requirement that the table carries a `source: title` column. The View validator raises `E_VIEW_LABELS_BOTH_TABLE_TITLE` without one. It names the combination the presets already rely on.

## Preset package (`presentation-preset-v0.1`, extended in place with optional fields)

5. **Legend.** An optional `resources.detailProfile` (kind `review-detail-profile`) is a fifth member. Draft render uses it unless `--detail` is given, just as explicit flags override the other members.
6. **Visual profile.** An optional `body.visualProfile: {preferred: <profile id>}`. A draft render with a preset uses it when `--visual-profile` is not given. An explicit flag always wins. The CLI default becomes "the preset's preferred profile, or `v0.5-baseline`". The target kind must match, otherwise `E_PRESET_VISUAL_PROFILE_TARGET`.

## Catalogue presets (criterion 7)

The five bundle Views and Themes drop HALCYON-specific values:
- `grouping.order: {by: earliestPlannedStart}`;
- `colorEncoding.domain: firstAppearance` with a Theme `palette` replacing the `owner` slot maps;
- `labels.placement: both` where names sit in both places;
- a bundle `detail.yaml` legend (Planned, Actual, Milestone), applied where the Layout has a `legend` slot;
- `elevated-light` with `visualProfile.preferred: chrona-output/visual/v0.7-svg`.

Tests render every preset against HALCYON-1 and the `chrona init` starter, and assert:
- no value from HALCYON's owner set appears in any bundle file;
- the starter (no `owner` field) shows no group header;
- the legend renders;
- `elevated-light` paints its gradient without a flag.

## Boundaries

Projection owns group order and domain derivation, the Theme owns the palette, Layout and Scene are unchanged, and the CLI selects the profile. There is no Scene or adapter change.

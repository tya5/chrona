# Procedure: a new chrona design from a brief, in YAML only

1. **Pick the closest bundle.** `chrona preset list`; prefer one whose description says
   "baseline drawn from --snapshot" if the brief needs a baseline. `chrona preset copy <id> --output looks/<name>`.
2. **Rename consistently.** Set the same new `id` in `theme.yaml`, `scheme.yaml`, `layout.yaml`, `view.yaml`,
   `detail.yaml`, and in `preset.yaml` (`id`, every `resources.*.id`, `compatibleColorSchemes`).
3. **Render the untouched copy first** on a realistic plan (groups, gates, relations, Actual, `--snapshot`)
   in every locale you need. Keep the warnings JSON; it is the baseline you compare against.
4. **Scheme (`scheme.yaml`): the palette.** `colors.surface` (paper), `text`, `textMuted`, `accent`, `rule`;
   `categories.*` are free slots that the Theme names as `category:<slot>`. Set `suitability.colorVision`
   to the deficiencies you claim; it turns on the simulated checks.
5. **Theme (`theme.yaml`), three parts:**
   - `values`: typed tokens. Fonts (`fontFamily`, list a CJK family too), sizes, `spacing.*`, row height
     (`timeline-row-height`), stroke widths, `radius` tokens (type `radius`, not `number`),
     `textTransform` (`small-caps` needs a `smallCapsScale` number token on the role), symbols
     (`{shape: circle}`; glyph paths accept `M L Z` only).
   - `roles`: which token each drawn role uses. Group header = `groupHeader`; today line = `as-of`
     (and `asOf`); milestone = `milestoneSymbol*`; bars = `planned`, `actual`, `snapshot`; rules =
     `row-rule`, `axis-*`; bands = `*-band` (`backgroundTreatment: none` removes a fill).
   - `colorBindings`: `<role>.<fill|stroke>: <scheme colour or category:slot>`. Today = `as-of.stroke`;
     planned milestone = `milestone.fill` and `gate.fill`; actual milestone = `actual.fill`.
6. **Layout (`layout.yaml`).** `root` is the page tree (rows, columns, slots by `source`). `viewDefaults` is
   the design half of the View: `shading`, `grouping` (drop `tint` if you drop `colorScales`),
   `backgroundDecoration`, axis `tiers` (drop `role: band` tiers for no filled header), `progressFill`
   (remove it if actual bars should be drawn as actuals). `requiredThemeTokens` must list exactly the
   tokens the tree uses, sorted.
7. **Detail (`detail.yaml`): the legend.** One `{role, label: {wording: key}}` per key; use wording keys
   (not literals) so the legend follows `--locale`. Roles not listed may still be added by default.
8. **View (`view.yaml`)**: usually unchanged; it connects plan data (selection, grouping key, columns).
9. **Iterate**: render en-US and ja-JP PNG, look at both, change one file, re-render.
10. **Checks before you stop:**
    - Set `contrastPolicy: {mark: error, stateText: error, groundText: error, decoration: error}`; the
      render must still exit 0. Accept only a reasoned `exceptions` entry (e.g. `purpose: dependency-halo`).
    - No `W_SCENE_*_CONTRAST`, `W_LAYOUT_TEXT_ELLIPSIZED`, `W_LAYOUT_VISIBLE_OVERFLOW`,
      `W_LEGEND_SWATCH_COLLISION`, `W_LEGEND_LABEL_DUPLICATE`, `W_PRESENTATION_SCALE_NOT_SEPARABLE`,
      `W_LEGEND_COLOR_NOT_SEPARABLE` in `warnings`.
    - `W_LEGEND_COLOR_NOT_SEPARABLE` only compares scale-encoded keys: for semantic keys compute
      CIEDE2000 of every legend-key ink pair under normal, protanopia, deuteranopia and tritanopia
      (`chrona.presentation.model.color_separability.delta_e_2000`) and require each pair ≥ 5.
    - Compare the warning list with step 3: any new code is yours to explain.

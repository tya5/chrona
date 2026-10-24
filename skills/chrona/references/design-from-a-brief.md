# A new design from a brief, in YAML only

Use this when the user describes a look ("an A4 grayscale board review", "a dark wallboard in our
brand colours") that no builtin preset matches. You copy the closest preset and edit its YAML; no
Python and no change to the plan. Run the commands from the skill directory. The example names the
copy `brief-look`.

## 1. Read the brief as claims

Write down what the brief promises before editing anything. Each promise is a claim that you will
check in step 9:

- the page: screen width, or a paper size such as A4 landscape;
- the readers: colour-vision deficiencies to support, and whether the design will be printed or photocopied;
- the locales the design must work in, such as `en-US` and `ja-JP`;
- what must be drawn: a baseline, actuals, gates, dependencies, notes, an owner column or a delta column.

## 2. Copy the closest preset

Pick by the description `chrona preset list` prints. If the brief needs a baseline, choose one that
says "baseline drawn from --snapshot". `--id` renames the preset and every resource id inside it
together, so you never rename by hand:

```bash
chrona preset list
chrona preset copy target-b --id brief-look --output looks/brief-look
```

The copy has six files: `preset.yaml`, `view.yaml`, `theme.yaml`, `scheme.yaml`, `layout.yaml` and
`detail.yaml`.

## 3. Render the untouched copy first

Render it on a realistic plan, one that has groups, gates, dependencies, actuals and a baseline. Do
this in every locale the brief names. Keep the JSON that `render` prints, because its `warnings` list
is the starting point you compare against in step 9:

```bash
chrona render examples/launch.yaml --actual examples/actual.yaml --snapshot examples/launch.yaml --preset looks/brief-look/preset.yaml --output brief-en.svg
chrona render examples/launch.yaml --actual examples/actual.yaml --snapshot examples/launch.yaml --preset looks/brief-look/preset.yaml --locale ja-JP --output brief-ja.svg
```

## 4. Scheme (`scheme.yaml`): the palette and its claims

- `colors` holds `surface` (the paper), `text`, `textMuted`, `accent` and `rule`. `categories.*` are
  free slots, which the Theme names as `category:<slot>`.
- `suitability` records what step 1 promised:
  - `colorVision` lists `deuteranopia`, `protanopia` and `tritanopia`, or `none-claimed`.
  - `print` is `print-friendly`, `photocopy-friendly` or `not-claimed`.

  These two are claims, not decoration. Without a claim, inks that look alike in the legend only
  warn (`W_LEGEND_COLOR_NOT_SEPARABLE`). With a `colorVision` claim, inks that look alike under that
  vision fail the render; with a `print` claim, inks that look alike in grayscale fail it. Make a
  claim only if the design really meets it.
- To keep two meanings apart, give them different lightness, not only a different hue. A key that
  differs in shape or line pattern, such as a dashed outline next to a solid bar, is already distinct.

## 5. Theme (`theme.yaml`): tokens, roles and colour bindings

- `values` holds the typed tokens:
  - fonts (`fontFamily`, which should also list a CJK family if the brief needs Japanese), sizes and
    `spacing.*`;
  - stroke widths and radii (a `radius` token has type `radius`, not `number`);
  - `textTransform` (`small-caps` also needs a `smallCapsScale` token on the role);
  - symbols, such as `{shape: circle}` (glyph paths accept only `M`, `L` and `Z`).
- `roles` says which token each drawn role uses. For example:
  - group headers: `groupHeader`;
  - the today line: `as-of`;
  - milestones: `milestoneSymbol*`;
  - bars: `planned`, `actual` and `snapshot`;
  - rules: `row-rule` and `axis-*`;
  - bands: `*-band` (`backgroundTreatment: none` removes a fill).

  If a role does not accept a property, the error lists the properties it does accept. The
  [Theme role reference](theme-role-reference.md) gives the full table.
- `colorBindings` maps `<role>.<fill|stroke>` to a scheme colour or to `category:<slot>`.
- Row height: `timeline-row-height` is a minimum, not the row pitch. Measured text line height, row
  padding and the mark size set the pitch, so to tighten rows for paper, reduce those as well.
- A Theme that `extends` a base may declare any member a standalone Theme declares, including
  `contrastPolicy`.

## 6. Layout (`layout.yaml`): the page

- `root` is the page tree: rows, columns, and slots filled by a `source`.
- `pageSize` gives the design its own paper, so no `--viewport` flag is needed. Use one of `a3-*`,
  `a4-*`, `a5-*`, `letter-*` or `legal-*`, each ending in `-portrait` or `-landscape`, for example
  `pageSize: a4-landscape`. Content that does not fit warns `W_LAYOUT_CANVAS_EXCEEDS_VIEWPORT`. For
  a screen size, pass `--viewport WIDTHxHEIGHT` instead.
- `viewDefaults` is the design half of the View: shading, grouping (drop `tint` if you drop
  `colorScales`), background decoration, axis tiers and `progressFill`.
- `requiredThemeTokens` must list exactly the tokens the tree uses, sorted.

## 7. Legend (`detail.yaml`)

Add one `{role, label: {wording: KEY}}` entry per key. Use wording keys, not literal text, so that the
legend follows `--locale`. A role that is drawn but has no key warns `W_LEGEND_ROLE_UNKEYED`. Either
add the key, or stop drawing the role.

## 8. View (`view.yaml`): the plan side

- A member the View declares replaces the Layout's `viewDefaults` member as a whole. For example, the
  copy's `visibility` block overrides a `visibility` change made in `layout.yaml`. Edit the member in
  the file that declares it, or delete it from `view.yaml` so the Layout default applies.
  `comparison`, `rows` and `window` are the exception: they merge one level down, so a sub-member the
  View declares wins and the others come from the Layout.
- A delta column against the baseline needs no flag. Add `snapshotFinishDelta` to
  `comparison.facets`, then add a column whose `source` is `{comparisonFacet: snapshotFinishDelta}`.
- Replace literal labels with wording keys (headings, the unassigned group, column headers), so that
  `ja-JP` does not show English and `en-US` does not show Japanese.

## 9. Iterate, then check against the claims

Change one file at a time. Validate it, then re-render each locale, and look at the pictures, not
only at the JSON:

```bash
chrona validate looks/brief-look/theme.yaml
chrona validate looks/brief-look/scheme.yaml
chrona validate looks/brief-look/layout.yaml
chrona validate looks/brief-look/detail.yaml
chrona validate looks/brief-look/view.yaml
chrona validate looks/brief-look/preset.yaml
```

`validate` checks one Theme, Scheme, Layout or legend file by its `kind`. The copied `view.yaml` is
only the plan half of a View; `validate view.yaml` finds the `preset.yaml` beside it and checks the View
with that preset's Layout defaults. `validate preset.yaml` checks the whole closure, every member file,
and names the file and pointer of each error.

Stop when all of these hold:

- Every locale renders with exit code 0, and you have looked at each picture.
- Strict contrast passes. Temporarily set `contrastPolicy: {mark: error, stateText: error, groundText: error, decoration: error}`
  in the Theme, and the render still exits 0. Keep an `exceptions` entry only with a reason, for
  example `purpose: dependency-halo`.
- The scheme's claims hold: the render succeeds with the `colorVision` and `print` claims set.
- The `warnings` contain none of the following:
  - `W_SCENE_*_CONTRAST`, `W_LAYOUT_TEXT_ELLIPSIZED` or `W_LAYOUT_VISIBLE_OVERFLOW`;
  - `W_LEGEND_SWATCH_COLLISION`, `W_LEGEND_LABEL_DUPLICATE`, `W_LEGEND_ROLE_UNKEYED` or
    `W_LEGEND_COLOR_NOT_SEPARABLE`;
  - `W_LAYOUT_CANVAS_EXCEEDS_VIEWPORT`, for a fixed page.
- Compared with the step 3 warnings, every new code is one you can explain.

[Diagnostics](diagnostics.md) explains each code.

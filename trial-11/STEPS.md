# trial11 step log (base origin/main cc2b237d1)

1. venv `.trial11/venv`, `pip install '.[render]'` (not editable).
2. Plan: `plan/gen.py` + `plan/build.sh` -> CSV -> `chrona import` (30 tasks, 6 gates, 5 groups, relations,
   Actual as of 2027-04-14, baseline = same plan before 4 tasks slipped), en and ja titles.
3. `chrona preset copy target-b --output .trial11/nordic` (closest: table+timeline, baseline drawn). Kept an
   untouched copy in `target-b-copy/`. Reference render: `out/targetb-*.png`.
4. Theme/layout edits by script (`edit_theme.py`, `edit_layout.py`, then `tweak.py` one-offs).
   Rejections met, in order:
   - `E_THEME_SCHEMA /body/values/dash.as-of/value/1: 0 is less than or equal to the minimum of 0`
     (tried `[1, 0]` for a solid line; fix: remove `dash` from roles `asOf`/`as-of`).
   - `E_DRAFT_PRESET_RESOURCE ... declares theme id 'target-b', but theme.yaml has id 'nordic-paper'` (clear).
   - `E_THEME_TOKEN_TYPE /body/roles/planned/cornerRadius ... declaredType=str, expectedType='radius'`
     (I had declared `type: number`; message says `str`).
   - `E_THEME_TOKEN_TYPE` at sourceRef `/`: `glyph path data is not valid normalized geometry
     (length=27, parser=IconNormalizationError)` for `M50 0A50 50 0 1 1 49.999 0Z`; no token named, arcs
     not said to be unsupported. Found `shape: circle` by grepping other bundles.
   - `E_LAYOUT_TOKEN_REQUIREMENT_EXTRANEOUS: no further detail is recorded for this code (legend-item-min)`.
   - `E_LAYOUT_TOKEN_REQUIREMENTS: requiredThemeTokens must be sorted` (clear).
5. Discovered by reading other bundles/schemas, not docs: `small-caps` + `smallCapsScale` (sunday),
   legend `columns` (sunday), `asOf` legend role (editorial), `shape: circle` (executive-light),
   `contrastPolicy.exceptions` shape (schema), which binding paints the today line (`as-of.stroke`, by
   reading the emitted SVG `data-purpose`).
6. Visual iterations: n1 (legend centre, mixed-case legend labels from wording table), n2 (legend top right
   but 2 rows overlap axis), n3 (one row), n4 (`Progress` key appeared by default; progress fill and actual
   both drawn), n5 (removed `viewDefaults.progressFill`; legend label ellipsized), n6/final (fixed legend width).
7. Colour: `separability.py` (chrona's own CIEDE2000 + CVD simulation) found planned vs non-working band
   ΔE 2.7 and actual vs today ΔE 0; fixed by darker planned fill, lighter band, actual in ink, accent only for
   today/slip. Contrast policy set to `error` for mark/stateText/groundText/decoration; render exits 0.

# Issue #588: hand-wobble stroke treatment and per-state value affixes (work record)

Living record for [#588](https://github.com/tya5/chrona/issues/588): baseline, design plan, design, architecture review, implementation plan and progress. Edited in place; Git keeps history.

**Public base:** `7028bf2c` on `main`. **Status:** design (PR #954) published; I588-1 hand wobble (PR #958) and I588-2 value affixes implemented (section 8); the acceptance review follows.

## 1. Published baseline

Issue #588 had no comments before this work (body unchanged since filing; the claim is the first comment). It is Depth B, low priority, the P4-B "Sunday" item of the board [#454](https://github.com/tya5/chrona/issues/454) (read only). The design target is [`sunday-target-2026-09-26`](../../research/presentation/sunday-target-2026-09-26/README.md) ("a hand-wobble line treatment that changes stroke geometry but not bounds"; "`+10!`, `?`: slip values with an exclamation, a missing actual as `?`", "no per-value text affixes by state"). Read on `7028bf2c` from code, specifications and the READMEs, not from the target images:

**Wobble**

1. **Stroke paint is a closed completed fact.** `resolve_scene_paint` (`scene/paint.py`) turns a Theme role into `ScenePaint` (fill, stroke, width, dash, opacity, gradient, shadow, stroke finish, image, glow). A treatment that a profile may not paint is a `decorative-optional` or `required` property with a fidelity, a capability ID and a `PaintOmission`; #587 added `glow` exactly this way (`effect.glow`, `_admit`, `I_VISUAL_TREATMENT_OMITTED`, `E_VISUAL_CAPABILITY_UNSUPPORTED`).
2. **Geometry is completed before Scene.** Layout fixes `ScenePrimitive.bounds`, a Path's `points` or `path_commands`, and corner radius. Scene paint completion already derives geometry-dependent paint from them (gradient endpoints from bounds, the glow region from a primitive's extent, `v05_builder._visible_extent`). Nothing in Layout, collision or the contrast gates reads paint.
3. **Adapters serialize.** `v05_svg` draws a Rect as `<rect>`, a Path as `<path d=...>` from `path_data`; the PNG adapter is that same SVG through the pinned resvg (`ResvgPngRenderer.render` calls `V05SvgRenderer`), so "SVG and PNG identical" holds by construction once the SVG is. Typst and TikZ do not draw gradient, shadow or glow; the Scene profile gate (`validate_surface_visual_profile`), not the adapter, rejects a required one. The baseline profile `chrona-output/visual/v0.5-baseline` carries `MARK_GEOMETRY_CAPABILITIES` only; the four rich profiles add `RICH_CAPABILITIES`.
4. **No wobble exists.** There is no Theme property, Scene field or adapter code for stroke perturbation, and no deterministic noise helper in `src/chrona` (checked by search for `random`, `hash(`, `noise`, `wobble`).
5. **Theme additions are in place** (Specification 56 section 3.2): #587 added `glow*` to `theme-v0.11` and `theme-v0.13` and `paint.glow` to `scene-v0.7` with no version bump; the S0 gate `python -m tools.schema_equivalence --base-rev origin/main` wanted one `conformance/schema-equivalence/expected-deltas-v0.1.yaml` entry per added Theme property, each naming a test.

**Affixes**

6. **A table cell is one string, normalised once.** `review/v05_content.normalize_v05_table_content` builds `TableCellContent(content, semantic_id, typography_role)` per cell with `display_value(value, column.missing, column.format)`; the same string feeds column measurement (`place_table_columns`) and placement (`layout/surface_table.py`). The Δ column of the Sunday target is a View `tableColumns` entry with `source: {facet: finishDelta}` or `{comparisonFacet: finishDelta}` and `format: signedDays` (`+10d`, an `int` of calendar days, positive is a slip, negative is ahead). A value of `None` renders the column's `missing` text (`blank`, `em-dash`, `unknown`, `in-progress`).
7. **The cell's semantic already knows the state** (`tableVarianceBehind`, `tableVarianceAhead`, `tableVarianceOnTrack`, `missingActualCell`), and Theme roles `variance-behind`, `variance-ahead`, `variance-on-track`, `missing-actual-cell` paint them. No text is added per state.
8. **Closed formats.** `vocabulary-v0.1` `tableColumnScalarFormat` is `text | dateRange | date | signedDays`; `signedDays` always writes the unit (`+10d`), so `+10!` cannot be expressed even with an affix.
9. **Overflow.** Under `table.overflow: ellipsize-with-source` a cell is ellipsized as one string (`surface_table.table_text`); under any other value it is drawn whole.
10. **View additions are in place** (#583 `grouping.header`, #582 `periods`): optional, no version bump, and an expected-delta entry because the View body sits under conditional composition.

Inferred (to be confirmed by the slice that touches it): that no primitive kind other than Rect and Path needs the wobble for the Sunday evidence; that `ScenePaint.glow`'s serialization path (`scene_document` selecting v0.7) is the right model for `wobble`.

Unverified: the rendered look of a wobble (read as images in the slice); the Windows run (no Windows host here; the three-OS CI is the check); how a wobbled outline composes with a clip host or a catalogue pattern (excluded by design, section 5.1).

## 2. Literal acceptance (copied from the issue)

1. A Theme stroke treatment `wobble` with a declared amplitude and seed. It is deterministic, and SVG and PNG are identical. Bounds used for layout are unchanged, and a test proves it.
2. A Theme/View value format declares affixes per state (slip, on-time, ahead, missing). Measurement includes the affixes, and synthetic tests cover each state.
3. Evidence: the Sunday slide through YAML.

Principle from the issue body: core gets general declarative knobs only, tested on synthetic fixtures; the targets are reached afterwards by preset/Theme/View YAML as evidence, not as a core pass condition.

## 3. Dependencies and neighbours

- #587 (closed) supplies the template: the paint-fact, capability ID and omission ladder pattern; the texture and glow are not changed. #583, #586 and #493 supply the View text-template patterns (View property, typed contract, content normalisation, one composition function, Layout reads the completed string).
- #718 (closed, parts catalogue), #889 (panels with gutters, open) and #888 (title border) are neighbours of the Sunday target; this work adds none of them.
- **Not touched:** #585 (text compression, vertical text) and #491 (axis corners) files; `layout/text.py`, axis modules, the Project schema, presets, catalogues and every corpus datum. #454 is read only.
- Shared files kept to minimal diffs: `schemas/theme-v0.11.schema.yaml`, `schemas/theme-v0.13.schema.yaml`, `schemas/scene-v0.7.schema.yaml`, `schemas/view-v0.28.schema.yaml`, `schemas/vocabulary-v0.1.schema.yaml`, `conformance/schema-equivalence/expected-deltas-v0.1.yaml`, `scene/capabilities.py`, Specifications 06, 07, 08, 63, the Controller Z manifest and the public-slide count tests (an evidence slide per slice).

## 4. Design plan

### Use cases

| Id | Use case | Target |
| --- | --- | --- |
| U1 | A Theme declares an ink outline that wobbles by up to 1.6 px with a wavelength of 22 px and seed 7 on the plan and actual bars. Two renders of any project are byte-identical; two bars differ from each other. | Sunday |
| U2 | The same Theme under the baseline profile: a `decorative-optional` wobble is omitted and reported with the profile that paints it; a `required` one fails before serialization. Typst, TikZ and PDF follow the baseline ladder. | #478 |
| U3 | A Theme declares a wobble on a connector role (dependency, axis rule): the line wobbles, its two end points and arrowheads stay put. | Sunday, Blueprint |
| U4 | Layout, collision and contrast results are identical with and without a wobble: the treatment is paint. | acceptance 1 |
| U5 | A Δ column declares affixes: a slip shows `+10!`, an on-time `+0`, an ahead `-3`, a missing actual `?`. | Sunday |
| U6 | The column width grows to hold the affixes; under ellipsis the affix survives. | acceptance 2 |
| U7 | A Theme and a View without the new properties render byte for byte as before. | default unchanged |

### Open decisions (closed in the design, recorded on the issue)

- **W1.** Where wobble is declared, and which primitives it reaches.
- **W2.** Who computes the perturbed geometry: Layout, Scene or the adapter.
- **W3.** The determinism contract: generator, seed meaning, per-primitive variation, float rules.
- **W4.** Capability, profile and fallback (baseline, Typst, TikZ, PDF).
- **W5.** Bounds, hosting and contrast implications.
- **A1.** Where affixes are declared (Theme or View) and what a state is.
- **A2.** What an affix is and how `?` and `+10!` are reached.
- **A3.** Measurement and overflow.
- **A4.** Which value sites are covered.
- **E1.** Committed evidence without editing corpus data.

### Responsibility boundaries

Theme declares the wobble (role properties); Scene completes the perturbed outline from the primitive's Layout geometry as part of paint completion (like the glow region); adapters serialize completed points and decide nothing. View declares affixes on a table column; content normalisation composes the final cell string; Layout measures and places that string and protects the affixes from ellipsis. Core rules name no target, preset or corpus file.

### Order of design slices

1. **D588** (this publication): baseline, design plan, design, architecture review, implementation plan.
2. I588-1 and I588-2 as planned in section 7, then the acceptance review.

## 5. Design

### 5.1 Wobble: declaration and reach (W1)

Theme role properties `wobbleAmplitude` (px), `wobbleWavelength` (px), `wobbleSeed` (non-negative integer) and `wobbleFidelity` (`required` or `decorative-optional`, default `required`), each a named Theme token like `glowBlur`. The first three are declared together or none (`E_VISUAL_CAPABILITY_VALUE`); `0 < amplitude <= 16`, `4 <= wavelength <= 1000` and `0 <= seed < 2^32` with an integral value are limits (`E_VISUAL_CAPABILITY_LIMIT`); fidelity is `E_VISUAL_CAPABILITY_FIDELITY`. The properties are admitted on the roles whose completed primitive is a Rect or a Path (`_RECT_PAINT` and `_PATH_PAINT`, not text, canvas, Icon-shared or shared `text` roles), and the closure's role admission and the Color Scheme rules need no new binding (no colour is added).

A wobble reaches **a Rect that has a stroke** (the filled rectangle and its outline both follow the perturbed outline, drawn as one closed path) and **a Path** (each sub-path). It does not reach a Symbol, Text or Icon, nor a Rect that carries a catalogue pattern or an image fill or that hosts a clip: a pattern region, an image tile and a clip are defined to equal the exact rectangle, and a perturbed outline would break that equality. A fill-only Rect has no stroke to treat and is drawn as before. These are rules of the treatment, stated in Specification 07, not diagnostics: a role shared by a bar and a gate wobbles the bar.

### 5.2 Wobble: who computes (W2)

Scene, in paint completion. Option A (the adapter perturbs from `amplitude, wavelength, seed`) would put the generator in an adapter and force each future adapter to reproduce it bit for bit. Option B (Layout perturbs) would make a paint-level distortion a Layout decision although no Layout result may depend on it (U4). Option C (chosen): `resolve_scene_paint` yields the parameters with the omission ladder; `v05_builder._complete_primitive_paint`, which already holds the primitive, calls one pure function `scene/stroke_wobble.py:complete_stroke_wobble(...)`, and the result is a typed completed fact on `ScenePaint`:

`StrokeWobble(amplitude, wavelength, seed, fidelity, closed, outline)` where `outline` is a tuple of polylines (tuples of `(x, y)` rounded to three decimals). Scene v0.7 gains the optional `paint.wobble` in place and a Scene that carries one is written as `chrona/scene/v0.7` (the glow precedent); v0.6 is the transitioning schema and is not edited. The adapter draws `outline` verbatim: a Rect as `<path d="M..L..Z">` carrying the Rect's fill, stroke and filter attributes, a Path as `<path d="M..L..">` with its markers. Reverse: move `complete_stroke_wobble` into the adapter and drop `outline` from the fact.

### 5.3 Wobble: the determinism contract (W3)

The algorithm is fixed by the specification and independent of platform, Python build, hash seed and iteration order.

- **Generator.** Integer-only. `mix(x)` is the splitmix64 finalizer on `x` masked to 64 bits (constants `0x9E3779B97F4A7C15`, `0xBF58476D1CE4E5B9`, `0x94D049BB133111EB`, shifts 30, 27, 31). A **lattice value** is `mix(stream ^ (k * 0xD1B54A32D192ED03 mod 2^64)) >> 11`, divided by `2^53`, doubled, minus one: an exact double in `[-1, 1)`.
- **Seed and per-primitive variation.** `stream = mix(mix(seed) ^ fnv1a64(utf8(scene_id)) ^ (subpath_index << 56))`. `fnv1a64` is the 64-bit FNV-1a over the UTF-8 bytes (not Python `hash`). The declared seed selects the whole pattern family and the primitive identity gives each bar its own line, so a Theme gives a hand that does not repeat itself; one primitive always gets the same line. The Scene id is stable for a project, a view and a context (it is already serialized in the Scene and in the SVG).
- **Noise.** Value noise on a lattice along the outline: arc length `s` maps to `u = s * n / P` with `P` the nominal perimeter or length and `n = floor(P / wavelength + 0.5)` cells (at least 2 for a closed outline, at least 1 for an open one), so the realised wavelength `P / n` divides the outline exactly and a closed outline closes without a seam. `v = L(k) + (L(k + 1) - L(k)) * w` with `w = t * t * (3 - 2 * t)`, `k = floor(u)`, `t = u - k`, and `k + 1` taken modulo `n` for a closed outline.
- **Operations.** Only `+ - * /` and `sqrt` on doubles (IEEE 754 correctly rounded, so identical on every conforming platform; CPython does not fuse multiply-add), `floor`, and integer arithmetic. No `sin`, `cos`, `pow`, `exp` or `hypot` (library results may differ in the last bit between C runtimes), no `random`, no `set` or `dict` order (outlines are tuples built in declaration order), and no float formatting other than the existing SVG `f"{value:.3f}"` (correctly rounded, locale independent) and `round(value, 3)` (correctly rounded).
- **Displacement.** Each outline vertex moves along its unit normal by `amplitude_effective * v * envelope`. `amplitude_effective` is the declared amplitude, limited for a Rect to a quarter of its shorter side so a thin bar cannot cross itself. An open outline tapers: `envelope = min(1, s / wavelength_realised, (P - s) / wavelength_realised)`, so both end points are fixed and a marker keeps its place and direction; a closed outline has envelope 1. Vertex normals are the normalised sum of the adjacent unit segment normals (a segment normal at an open end); a closed outline runs clockwise from the top-left so the normal points outward.
- **Resampling.** Every nominal edge is split into `max(1, ceil(length / (wavelength_realised / 4)))` equal parts, keeping each original vertex (corners stay corners). A rounded Rect corner is first flattened to the quadratic Bézier with the sharp corner as control point at `t = 0.25, 0.5, 0.75`; a Path's quadratic commands are flattened the same way with four steps. An outline over 8192 points is `E_VISUAL_CAPABILITY_LIMIT` at `wobbleWavelength`.
- **Pins.** A unit test holds the first lattice values for fixed `(seed, id)` and the SHA-256 of one fixed outline's serialization; the three-OS CI therefore compares Windows, macOS and Linux against the same constants.

### 5.4 Wobble: capability, profile and fallback (W4)

`stroke.wobble` is a new ADMITTED capability (owner Theme) in the closed ceiling and joins `RICH_CAPABILITIES`, so the four rich SVG/PNG profiles paint it and the baseline does not. Under the baseline a `decorative-optional` wobble is omitted with `I_VISUAL_TREATMENT_OMITTED:role=<role>;treatment=wobble;profile=chrona-output/visual/v0.5-baseline;paintable=<first rich profile for the target>` (a `PaintOmission` treatment `wobble`, source ref `/body/roles/<role>/wobbleAmplitude`) and the primitive is drawn straight; a `required` wobble fails before serialization with `E_VISUAL_CAPABILITY_UNSUPPORTED`. Typst, TikZ and PDF contexts use the baseline profile, so they follow the same ladder and their adapters never receive a wobble. As a second line of defence the Typst and TikZ adapters refuse a Scene that carries a `required` wobble (`E_VISUAL_CAPABILITY_UNSUPPORTED`, as they refuse a pattern) and draw an optional one straight. Judgement call (recorded on the issue): the baseline SVG adapter could draw the outline, but the baseline is the portable floor that every target honours, and a stroke whose geometry differs from the Layout geometry is a rich treatment; joining the existing rich profiles instead of minting a profile identifier follows the glow decision.

### 5.5 Wobble: bounds, hosting and contrast (W5)

The primitive's `bounds`, `points` and `path_commands` stay the Layout values. The perturbed outline moves each vertex by at most the effective amplitude (declared limit 16 px), so the visible extent of a wobbled primitive is its bounds grown by at most that amplitude plus half the stroke width, like a stroke or a halo already is; it does not enter any bound. Consequently hosting, collision, label placement, the contrast ground lookup and the perceptibility observations are unchanged by construction, and a Rect's inside label sits on its nominal rectangle with at most amplitude of the fill's edge perturbed. Contrast needs no new rule: the colours are the role's. A glow on the same role keeps the region computed from the nominal extent (the halo loses at most the amplitude of reach at one end; the region is still clipped to the canvas). A test asserts every Scene primitive's bounds and ids, the placement list and the diagnostics equal with and without the treatment.

### 5.6 Affixes: declaration (A1, A2)

View `tableColumns[].affixes`, an optional object (Specification 56 section 3.2: in place in `view-v0.28`, omission is today's behaviour). Keys are the four states and each value is `{prefix?, suffix?}` with at least one non-empty string:

```yaml
- id: Δ
  source: {facet: finishDelta}
  format: signedNumber          # +10, +0, -3 (new scalar format, no unit)
  missing: blank
  affixes:
    slip:   {suffix: "!"}       # value > 0
    onTime: {}                  # not declared: unchanged
    ahead:  {}                  # not declared: unchanged
    missing: {suffix: "?"}      # value is None: blank + "?" is "?"
```

States: for the signed formats (`signedDays`, `signedNumber`) `slip` is a value above zero, `onTime` zero and `ahead` below zero (the three variance roles of Specification 04 and 08); `missing` is a `None` value of any format. A prefix or suffix is 1 to 8 characters, no control characters or line breaks; text and markup are literal (the SVG adapter escapes). The affix wraps the **formatted state text**, including the `missing` text, so `missing: blank` plus a `?` suffix reads `?` and `missing: em-dash` plus `?` reads `—?`. The state is derived from the value, never from the text. Judgement call (recorded on the issue): View, not Theme, because content strings are fixed before measurement and Theme is read by Layout, not by content normalisation; #583's header template is the precedent. A Theme-level mapping would need a second channel into content and would break "measure what you draw once".

`signedNumber` is added to the View table-column `format` as one more `oneOf` alternative declared in `view-v0.28` (`const: signedNumber`): `+10`, `+0`, `-3`, typography role `numeric` like `signedDays`. The shared `vocabulary-v0.1` part is frozen (a change is a new part version, never an edit; `test_vocabulary_part` enforces it), so the value is declared at the one site that uses it until that part has a new version. It exists because `signedDays` always writes the unit, and `+10!` (no unit) is the target. Reverse: remove the alternative; a Δ column then reads `+10d!`.

Failures at the contract (`E_VIEW_COLUMN_AFFIX`, one new code, the column id and the state named): an unknown state key, a `slip`, `onTime` or `ahead` entry on a column whose format is not signed, an entry with no non-empty prefix or suffix, a prefix or suffix over 8 characters or with a control character. Nothing is clamped or ignored.

### 5.7 Affixes: measurement and overflow (A3)

The cell string with affixes is composed once in `normalize_v05_table_content`, so `place_table_columns` measures it (a `content` column widens by the affix width) and `layout/surface_table.py` places the same string. `TableCellContent` gains `affix_prefix` and `affix_suffix` (default empty). Under `ellipsize-with-source` Layout ellipsizes the **core** (the formatted state text) within the available width minus the measured affixes, so a slip keeps its `!`; when the affixes alone exceed the available width the whole string is ellipsized by the existing rule. Under other overflow values the string is drawn whole, as today. The table cell's semantic and Theme role (`tableVarianceBehind` and its text role) are unchanged: the affix takes the cell's paint.

### 5.8 Affixes: coverage (A4)

Table columns only. The lane member `+Nd` chips (`surface_member_labels`, `lane_label_intent`), the summary metrics and the Detail `comparison-delta` label keep their strings; each has its own formatting rule (`detail.formatting`), and the Sunday Δ column is a table column. Recorded as a disclosure, not a literal acceptance gap: row 2 asks for "a Theme/View value format" and the table column format is one.

### 5.9 Committed evidence (E1)

Controller Z gains two slides, YAML only, no preset, catalogue or corpus datum edited: `hand-wobble` (I588-1: a dark or paper Theme with ink outlines that wobble on the bars, gates and connectors, under the rich SVG profile) and `value-affixes` (I588-2: a table View whose Δ column declares affixes, on the wobble Theme, so the slide combines both treatments). Both are rendered through resvg and read in full. The Sunday target also needs panels, the Ben-Day bands (a catalogue pattern, expressible today), balloons and the burst; the panels are #889, so acceptance row 3 is expected to be `narrowed` with #889 and the balloons as successors, unless the review finds otherwise.

### 5.10 Intended incompatibilities and failure behaviour

None for existing documents: every property is optional and absent output is unchanged (every committed Scene and SVG stays byte-identical, which proves only that the default is unchanged). New failures use existing codes (`E_VISUAL_CAPABILITY_*`, `E_THEME_ROLE_PROPERTY_UNSUPPORTED`) except `E_VIEW_COLUMN_AFFIX` (registered in `usecases/diagnostic_messages.py`).

## 6. Architecture review

- **Ownership.** Theme declares; Scene completes the outline from Layout geometry and resolves the ladder; adapters serialize points. View declares; content normalisation composes; Layout measures and places. No adapter reads Theme, Scheme or profile; no new Layout-to-Scene back channel; `scene/stroke_wobble.py` imports `surface_quality` types only (`tools/check_import_direction.py` expected green).
- **Determinism.** Integer generator, exact 53-bit conversion, IEEE basic operations and `sqrt` only, no library transcendental, no hash or order dependence, pinned by constants in tests. Cannot verify locally: a Windows run (no host); the pinned constants make the three-OS CI the check. The PNG raster is one resvg on one OS per run; a cross-OS raster comparison is not claimed (the existing PNG evidence has the same property).
- **Default output.** No property, no field, no filter, no string is written unless declared. Counting tests that depend on the public slide count change once per evidence slide.
- **Regression surface.** Wobble: the paint resolver, the capability ceiling and rich set, role admission, serialization and schema, the SVG Rect and Path branches (the straight branches are untouched). Affixes: the View schema and contract, `display_value` callers (one added optional argument), `TableCellContent`, the table cell ellipsis branch.
- **Layering with neighbours.** #587's texture and glow are untouched; a wobbled Rect that also has a glow keeps one `filter` attribute (glow) on the `<path>`. #585 and #491 files are not edited. #583 and #586 string composition is not read.
- **Risks.** (1) A very long outline at a small wavelength is large; the 8192-point limit and the 4 px floor bound it. (2) A wobbled bar's outline crosses neighbouring bars' gaps by at most the amplitude; Layout gaps are not widened (disclosed). (3) A role shared by a bar and a gate wobbles only the bar (documented). (4) `signedNumber` is declared in `view-v0.28` and not in the frozen shared vocabulary; the S0 gate entries name its test.
- **Extension points.** A second noise basis (e.g. sine) would be a new property with its own declared algorithm, never a change to this one; a wobble on Symbol or Icon needs outline flattening of those shapes (not designed); lane chips with affixes would reuse the same affix mapping.
- **Decision:** approved for implementation planning.

## 7. Implementation plan

Each code PR is `Refs #588`, carries the S0 gate result when it touches a schema, regenerates nothing by hand (the derived sync regenerates evidence; locally it is regenerated into a scratch directory to inspect), and leaves every committed example byte-identical except its own new slide.

### I588-1: hand wobble

- **Files.** `src/chrona/presentation/scene/stroke_wobble.py` (new: generator, noise, outline completion; pure); `scene/model.py` (`StrokeWobble`, `ScenePaint.wobble` as the last field); `scene/paint.py` (`_wobble`: limits, together-or-none, fidelity, omission); `scene/capabilities.py` (`STROKE_WOBBLE`, entry, the four properties on `_RECT_PAINT` and `_PATH_PAINT`); `scene/visual_capabilities.py` (rich set, profile gate); `scene/v05_builder.py` (call `complete_stroke_wobble` for an applicable primitive; exclusion rule); `scene/serialization.py` and `schemas/scene-v0.7.schema.yaml` (`paint.wobble`, version choice); `schemas/theme-v0.11.schema.yaml` and `theme-v0.13.schema.yaml` (four role properties; the S0 gate classifies them additive, and an expected-delta entry is added only if the gate asks); `model/info_diagnostics.py` (`wobble` treatment); `renderers/v05_svg.py` (Rect and Path outline branches); `renderers/v05_typeset.py` (the one-line guard); `tools/check_scene_primitive_delivery.py` and `tools/presentation_prior_art.py` (delivery owner, matrix row); Specifications 07, 08 and 63; Controller Z `hand-wobble` (Theme, context, manifest entry).
- **Tests (synthetic, no `examples/` input).** Unit: the generator and lattice pins; the outline of a fixed Rect, rounded Rect and Path (closed seam, fixed ends, vertices within amplitude, point counts, corners kept, a thin Rect's amplitude limit, two ids differ, same id equal, seed changes the line); resolution (limits, together-or-none, fidelity, applicability: pattern, image, clip host, fill-only, Symbol); the ladder (omission text, required failure, suggested profile); serialization and schema validity. Integration through `tests/support/synthetic_review.py`: SVG `<path>` shape for a Rect and a Path, the PNG raster through resvg (ink at displaced positions, none at the nominal edge, endpoints and arrowhead unmoved), two renders byte-identical, a Theme without the properties byte-identical to the base render, **bounds, ids, placements and diagnostics equal with and without the treatment**, Typst and TikZ following the ladder.
- **Mutation checks.** Break each rule and require a failure: tapering removed, amplitude limit removed, seam (modulo) removed, wrong step count, `scene_id` dropped from the stream, seed ignored, `hypot` or `sin` substituted (golden pin), closed outline not closed, bounds changed, pattern Rect wobbled, capability missing from the rich set, `required` omitted, optional failed, serialization missing. Results are listed in the PR.
- **Gates.** Focused tests, scene, layout and closure suites, `conformance/run_conformance.py`, `tools/check_import_direction.py`, `tools/regenerate_public_examples.py --check` (only the new slide may change), the S0 gate, the PR checks including `derived-ready`. A rendered image of the new slide and of probe renders is read in full.
- **Boundary.** One PR, merged with the merge lock; the next PR bases on the derived-sync bot commit.

### I588-2: per-state value affixes

- **Files.** `schemas/view-v0.28.schema.yaml` (`tableColumns[].affixes`), `schemas/schema-inventory-v0.1.yaml` (regenerated with `tools/schema_inventory.py` if the inventory asks), `conformance/schema-equivalence/expected-deltas-v0.1.yaml`; `presentation/contracts/resources.py` (`TableColumn.affixes`, `ColumnAffixes`, validation `E_VIEW_COLUMN_AFFIX`); `presentation/model/surface_content.py` (`display_value`'s affix argument, `TableCellContent` fields); `review/v05_content.py` (compose, numeric typography for `signedNumber`); `layout/surface_table.py` (ellipsis of the core only); `usecases/diagnostic_messages.py`; Specifications 06 and 08 or 50 (the cell rule); Controller Z `value-affixes` (View, context, manifest entry).
- **Tests.** Unit: each state (slip, onTime, ahead, missing) for `signedDays` and `signedNumber`, prefix and suffix, `missing` with each `missing` mode, no affix for a non-signed value, the contract failures; measurement (a `content` column is exactly as wide as with the affixes typed into the value); overflow (ellipsis keeps the affix; affix wider than the cell falls back to whole-string ellipsis; visible overflow draws whole). Integration: synthetic Project rendered with `+10!`, `+0`, `-3`, `?`; default byte identity.
- **Mutation checks.** State boundary off by one (zero as slip), affix applied to the wrong state, `missing` affix applied to non-`None`, affix dropped from measurement, ellipsis cuts the affix, prefix and suffix swapped, signed format on a non-int.
- **Gates and boundary.** As I588-1; merged alone after I588-1.

### I588-3: acceptance

`docs/reviews/current/issue-588-hand-wobble-and-value-affixes-acceptance-review-2026-10-02.md` with `<!-- chrona:literal-acceptance/v1 -->` and one row per literal criterion; any narrowed row names successor issues found by a duplicate search; `tools/check_issue_acceptance_reviews.py` run unpiped; merged; the exact-main three-OS run on the review-bearing commit located; #588 closed only when every row is met or narrowed with a successor and that run is green.

## 8. Progress and evidence

### I588-1 (PR #958): hand wobble

- **As designed,** with one addition: the Typst and TikZ adapters refuse a `required` wobble (section 5.4). `scene/stroke_wobble.py` is the pure generator and outline; `v05_builder._complete_wobble` applies it (stroked Rect without pattern, image or clip host; Path) and drops it elsewhere; Specifications 07, 08 and 63 section 8 carry the rule.
- **Default unchanged.** Regenerating every public slide changes only the new Controller Z `hand-wobble` slide.
- **Tests.** `tests/unit/chrona/presentation/scene/test_stroke_wobble.py` (generator and digest pins, bounds, seam, ends, limits, resolution, ladder, admission), `test_stroke_wobble_applicability.py` (where it applies, clip host through a real surface, profile gate, point limit), `tests/integration/test_stroke_wobble_render.py` (SVG shape, bounds and every primitive equal once the wobble is stripped, PNG pixels, determinism, v0.7 and schema, ladder, typeset refusal).
- **Mutation checks (35, all killed).** Three survived at first (sub-path stream, closed-outline point limit, the direct profile gate) and each got a test.
- **Rendered check.** The slide read through resvg: bars and dependencies are visibly hand-inked, corners stay corners, both ends of a dependency and its arrowhead stay put, nothing else moved. The corpus contrast gate reports 0 errors.
- **S0 gate.** Scene v0.7 and Theme v0.11 and v0.13 are classified additive. Against `origin/main` the gate also reports four pre-existing chained entries of #584 (`values/additionalProperties/allOf`) as "does not apply": they are not this work's and were left untouched; with them removed in a scratch copy the gate passes.

### I588-2: value affixes

- **As designed.** View `tableColumns[].affixes` (state to `{prefix, suffix}`), `signedNumber`, `E_VIEW_COLUMN_AFFIX`; `table_presentation.py` holds the typed values and the value-to-state rule; `review/v05_content.py` composes the cell once and carries the affixes; `layout/surface_table.py` cuts only the core under ellipsis.
- **Internal choice recorded here.** When the affixes leave no room for a character beside an ellipsis, Layout keeps the whole-string ellipsis instead of showing an affix next to nothing (a slip would otherwise read `!!`).
- **Tests.** `tests/unit/chrona/presentation/test_table_affix_state.py`, `tests/integration/test_table_affixes_render.py` (each state, prefix and suffix, `signedDays` and the missing text, default, measurement equal to typing the affix into the value, ellipsis, failures). **Mutation checks (17, all killed;** two survived at first and got tests).
- **Evidence.** Controller Z `value-affixes` (View v0.28, Theme derived from `capabilities` with the wobble properties, rich SVG profile): the Δ column reads `+4!` and `?`, the column is as wide as its text, the bars are hand-inked.

# Issue #491: axis cell corners (work record)

Living record for [#491](https://github.com/tya5/chrona/issues/491): baseline, design plan, design, architecture review and implementation plan. Edited in place; Git keeps history. Normative behavior lives in [Specification 39](../../specification/39-axis-and-observation-clarity.md), "Axis cell corners (#491)".

**Public base:** `7028bf2c` on `main`. **Status:** this record is the design publication (docs only, no code); implementation slices are section 7.

## 1. Published baseline

Issue #491 has no comments before my claim (body read 2026-10-02). It was filed from #426 acceptance row 10 and is the P4-B item of the axis lane after #492 (ticks) and #493 (secondary label), whose records are the model for this one ([#492](../archive/planning/issue-492-axis-ticks-design-plan-2026-10-02.md), [#493](../archive/planning/issue-493-axis-secondary-label-2026-10-02.md)).

Read on `7028bf2c`:

1. **A band cell is always a square Rect.** `layout/surface_axis.py:compose_axis`, `tier.role == "band"` branch, emits one `ShapePlacement(f"axis-band-rect:{tier}:{index}", "timeline-axis", "Rect", ...)` per interval. Its inline extent is the interval inset by half the band role's `cellGap` at both ends, except the outer end of a cell at the window edge, which reaches the plot edge (#880, `extend_to_plot_edges`). Its block extent is the declared lane, the tier's own lane (two or more band tiers), or the whole axis slot (exactly one band tier, historical geometry). `ShapePlacement.corner_radius` and `path_commands` exist and are unused here.
2. **Layout already carries corner and outline geometry for other shapes.** Marks, chips, legend swatches and progress fills pass `corner_radius` (a Rect `rx`) through Scene; annotation balloons and tilted notes pass `path_commands` through Scene as a `Symbol` outline (`annotation_tilt.polygon_commands` builds a closed polygon). A catalogue pattern is completed against a `Rect` placement with its `corner_radius` (`surface_completion.complete_catalog_patterns`), and the adapter checks the pattern's radius equals the Rect's.
3. **Scene projection drops both.** `scene/v05_builder.py` (the `axis_band_semantic_ids` branch) builds `ScenePrimitive(..., PrimitiveKind.RECT, ...)` from the placement bounds only. Scene primitives have `corner_radius` and `symbol`; no Scene or schema change is needed to carry either.
4. **Adapters.** SVG (and resvg PNG, which rasterises that SVG) draws a Rect's `corner_radius` as `rx`/`ry` and a `Symbol` as a filled `<path>`. The TikZ adapter draws both (`rounded corners=`, a path of line commands). The Typst adapter draws a Rect with `radius:` and rejects any `Symbol` with `E_VISUAL_CAPABILITY_UNSUPPORTED` (v05_typeset.py; the same gate already rejects glyph marks).
5. **Gates.** `scene/perceptibility.py` treats only `Rect` primitives as opaque occluders of text (`_occlusion_findings`); a hosted axis label is related to its band cell by `hostPlacementId` (`surface_quality` requires the host of an axis label to be an axis band `ShapePlacement`); `I_SCENE_PAINT_CONTRAST` reads each filled primitive against the canvas. A cell drawn as a `Symbol` would silently leave the occlusion gate unless the gate is taught about it.
6. **Theme.** `cellGap` (a named number token on the band role) is declared in `schemas/theme-v0.11` and `theme-v0.13`, admitted in `scene/capabilities.py` (`_LAYOUT_GEOMETRY`, role `axis-band-decoration axis-band-decoration2`, `scene_kinds = Rect`). The two band roles are bound to the first and second `band` tier (#426). No Theme property names a corner.
7. **Targets** (read as pictures and READMEs, `docs/research/presentation/`): Off-World "chamfered quarter tier, numbered month tier, week ticks" (README row "HUD ruler"; the picture shows the quarter cells as tabs with the two upper corners cut and a ruled outline); Sunday Strip shows the quarter band as yellow cells with slightly rounded corners and a thin outline. Which corners are cut is read from the picture, not from text that names it.

**Unverified at baseline:** how `unit` cells narrower than the cell block size behave under a radius (the rule below is a decision, section 5); whether Scene accepts a `Symbol` primitive with a band role's purpose and visual role without a registry change (checked by the first test).

## 2. Literal acceptance (copied from the issue)

1. A band tier's Theme role can declare a corner shape (radius or chamfer) for its cells, and one committed slide shows it.

## 3. Dependencies and neighbours

- #426 (lanes, `cellGap`, band roles), #880 (plot edge cell), #492 and #493 (same function, other branches) are closed and supply the mechanisms reused here. Only the `band` branch of `compose_axis` is touched.
- Other agents work on #585 (text compression and vertical text) and #588 (wobble, affixes): neither touches `surface_axis.py` band geometry; shared files are the two Theme schemas (`theme-v0.11`, `theme-v0.13`), `scene/capabilities.py`, `usecases/diagnostic_messages.py` and Specification 39. Diffs there are one added line or entry each and every PR rebases on `origin/main` before publication.
- No preset or catalogue Theme is edited: adopting a corner in a preset is a preset-owner decision (#718 area).

## 4. Design plan

### Use cases

| Id | Use case | Target |
| --- | --- | --- |
| U1 | A quarter or month cell has rounded corners | Sunday Strip |
| U2 | A quarter or month cell has cut (chamfered) corners | Off-World |
| U3 | Cells with a `cellGap`, abutting cells (gap 0), the first and last cell of the window | all |
| U4 | A cell narrower than the corner size still renders and the reduction is recorded | dense axes |
| U5 | A Theme that declares nothing renders byte-identically | every committed example |
| U6 | An impossible value (zero, negative, above half the cell, both shapes) is a typed error, not a clamp | all |

### Open decisions (closed in section 5)

- **D1 where the corner is declared.** The View band tier, or the Theme band role.
- **D2 vocabulary.** A composite token (`{shape, size, sides}`), or two ratio number tokens.
- **D3 the measure.** Px, a ratio of the cell block size, or a ratio of the cell's smaller side.
- **D4 a cell narrower than the corner.** Error, per-cell reduction with a record, or square corners.
- **D5 neighbours.** Shared edges, first and last cell, gaps, and whether a cell knows its neighbours.
- **D6 chamfer carriage.** A `Symbol` outline already in Scene, or a new Scene Rect member.
- **D7 corner shape and Theme patterns.**
- **D8 which corners.** All four, or per side (Off-World's tab).
- **D9 the Typst adapter.**

### Responsibility and architecture review questions

- Is the corner appearance Theme-owned (the View tier stays content and unit) and the completed outline Layout-owned, with Scene and the adapters only serialising it?
- Is the size measured relative to the cell, with no px constant in Layout and no table of cell sizes?
- Does a corner ever leave the cell rect, and so the axis slot, and does the cell keep its identity (`axis-band-rect:<tier>:<index>`), host relation, paint order and visual role?
- Do the Scene gates still see the cell ground: a hosted label's host, occlusion by a cell, paint contrast?
- Does the addition follow Specification 56 section 3.2 (an optional Theme role property, behavior-preserving) and pass `python -m tools.schema_equivalence --base-rev origin/main` with no expected-delta entry?
- Byte identity: no declaration means the same primitives for all committed slides.

### Acceptance evidence planned

Synthetic tests only, no `examples/` input: geometry from the Scene's own scale for radius and chamfer, with and without `cellGap`, first and last cell, a narrow cell, a lane-less single band and a lane band; every error and the warning; the occlusion and host gates on the produced Scene; default byte identity; adapters (SVG string, a resvg PNG pixel probe at a corner and at the centre, the Typst typed failure and Typst radius, TikZ). Mutation checks on the new tests. The S0 gate result in the schema PR. Rendered images read in full. One committed slide, and the literal acceptance review.

## 5. Design

### 5.1 Declaration (D1, D2, D3, D8)

Two optional **Theme role properties** on the band roles (`axis-band-decoration`, `axis-band-decoration2`), each a named number token beside `cellGap` (Theme v0.11 and v0.13, in place; `additive` under Specification 56 section 3.2):

| Property | Meaning |
| --- | --- |
| `cellCornerRadius` | Rounded corners: the arc radius, as a ratio of the cell's block size (its lane height). |
| `cellCornerChamfer` | Cut corners: the length of the cut along each edge at the corner, as a ratio of the cell's block size. |

Each applies to all four corners of every cell of the tier bound to the role. A ratio is `0 < ratio <= 0.5` (a corner cannot take more than half of the block size). The declaration names appearance only; which unit and how many cells is the View tier's, unchanged.

### 5.2 Static validation (U6)

Layout reads the properties once per band tier, before geometry, with the diagnostics family the band lanes and ticks use:

| Condition | Result |
| --- | --- |
| both properties declared | `E_PRESENTATION_AXIS_INVALID`, detail `cell-corner-both:<tier>` |
| a ratio not above 0, or above 0.5 | `E_PRESENTATION_AXIS_INVALID`, detail `cell-corner:<tier>` |
| `cellCornerChamfer` and a Theme `pattern` on the same role (D7) | `E_PRESENTATION_AXIS_INVALID`, detail `cell-chamfer-pattern:<tier>` |

Nothing is clamped. A non-number value fails with the existing Theme token error.

### 5.3 Geometry (D5, clipping)

Let `H` be the cell's block size (`band_block_size`, the lane or the slot) and `W` the cell's inline size after the `cellGap` inset and the plot-edge extension (the rect Layout draws today). The requested size is `s = ratio * H`.

- **Cell width limit (D4).** The applied size is `r = min(s, W / 2)`. When `r < s` the corner is reduced for that cell, Layout records `W_LAYOUT_AXIS_CELL_CORNER_REDUCED:<placement id>` (one per reduced cell) and the cell keeps its identity. A cell of zero width is drawn without a corner. A reduction is never silent and never an error: this is a per-cell consequence of the window and unit, like thinning (#482) and the secondary omission (#493), not a Theme mistake.
- **Radius.** The placement stays `Rect` with `corner_radius = r`; Scene projects `corner_radius`; adapters draw `rx`. A catalogue pattern keeps working because the pattern is completed with the same radius.
- **Chamfer.** The placement is a new `ShapePlacement` kind `Chamfer` whose bounds are the cell rect and whose `path_commands` is the closed eight-point polygon `(x+r,y) (x+W-r,y) (x+W,y+r) (x+W,y+H-r) (x+W-r,y+H) (x+r,y+H) (x,y+H-r) (x,y+r)`, built with the existing `polygon_commands`. Scene projects it as a `Symbol` primitive with the band's purpose and visual role, the same paint order and the same scene id.
- **Shared edges, first and last cell, gaps (D5).** A cell does not know its neighbours: every cell of the tier has the same corner rule applied to its own rect. With a `cellGap` the cells are separate tiles. With no gap (abutting cells) the corners open a notch at each shared edge that shows what lies under the axis (a rounded or cut join, the usual "tab" look); an author who wants a continuous band leaves the property out. The first and last cell take the corner on their outer corners too, including the cell that reaches the plot edge (#880): the window-edge cell is a cell like any other. The cell's own size, not the interval's, is `W`, so a gap does not change the ratio's meaning.
- **Clipping to the axis slot.** The outline lies inside the cell rect (every point has `x` in `[x, x+W]` and `y` in `[y, y+H]`), and the cell rect lies in the axis slot as today, so a corner only removes area and never paints outside the slot.
- **Hosting.** A label keeps its host: the host is chosen by bounds from the same `ShapePlacement` list, and `Chamfer` placements with a band semantic id are accepted wherever a band `ShapePlacement` is (`surface_quality` host check, `surface_completion.shape_slot`, `place_axis_band_visuals`). A label's rect lies inside the cell for any ratio (the label's lane is the cell's lane), though the corner may cut the label's box where it nears the cell edge; that is the reduced available area an author accepts and the label fit already measures against the cell's own inline size, not its outline.

### 5.4 Scene, adapters, gates (D6, D9)

- **Scene.** No new Scene member or schema. A radius sets `ScenePrimitive.corner_radius` (a Rect), a chamfer is a `Symbol` with `SymbolGeometry(path_commands)`. `scene/capabilities.py` admits `Symbol` for the band role next to `Rect` and the two properties as layout geometry.
- **SVG and PNG (resvg).** Radius: `<rect rx ry>`. Chamfer: a filled `<path>`. The PNG is the resvg rasterisation of that SVG and is probed at a cut corner and at the cell centre in a test.
- **TikZ.** Both are drawn by the existing Rect and Symbol branches.
- **Typst.** A radius is drawn (`#rect(..., radius:)`). A chamfer is a Scene `Symbol`, which the Typst adapter rejects with `E_VISUAL_CAPABILITY_UNSUPPORTED`, the same typed failure it already gives a glyph mark; the adapter is not extended here (a closed polygon via Typst `polygon` is an additive successor). A Theme that uses a chamfer therefore cannot be rendered through Typst until then, and this is documented, not hidden.
- **Gates.** The occlusion gate must keep seeing a cell as ground: it now also treats a filled, opaque `Symbol` whose visual role is a registered axis band role (read from the semantic registry, not a name list) as an occluder by its bounds, which for a cell whose outline lies inside its bounds is conservative. Hosting, `I_SCENE_HOSTED_TEXT_OVERLAP` and `I_SCENE_PAINT_CONTRAST` already read bounds, host ids and paint and are unchanged. A test proves the gate reports `E_SCENE_TEXT_OCCLUDED` for text covered by a later chamfered cell and no error for hosted labels.

### 5.5 Schema and migration

Two optional properties are added in place to `theme-v0.11` and `theme-v0.13` (the shape of `cellGap`). `python -m tools.schema_equivalence --base-rev origin/main` runs and its result goes in the PR; both are `additive`, so no expected-delta entry is added or edited. No version bump, no corpus migration; a Theme that declares neither renders the same primitives.

### 5.6 Owner decisions (also posted on #491)

| Id | Options | Choice | Why | How to reverse |
| --- | --- | --- | --- | --- |
| D1 | A Theme band-role property; B View band-tier member | A | the corner is appearance and every Theme that styles a band already owns `cellGap`; B puts presentation in content | add a View member that overrides the Theme later; A stays valid |
| D2 | composite token `{shape,size,sides}`; two ratio number tokens | two number tokens | a new token type edits the shared `values` oneOf in both Theme schemas and large expected-delta entries owned by others; two optional properties are additive and cannot conflict | add a `cornerShape` token type later and deprecate nothing |
| D3 | px; ratio of the block size; ratio of the smaller side | ratio of the cell's block size | the lane height is the stable cell dimension (inline size varies per unit and window); the limit `0.5` then has one meaning | none needed |
| D4 | error; reduce per cell with record; square | reduce with `W_LAYOUT_AXIS_CELL_CORNER_REDUCED` | a day axis would otherwise fail on its narrow cells; matches thinning and omission records | make it `E_PRESENTATION_AXIS_OVERFLOW` by one line |
| D5 | cells know neighbours (outer corners only); every cell alike | every cell alike | no new knob, no neighbour dependence on thinning or window; gap 0 gives a notch by design | a `cellCornerScope` property (additive) for tier-end-only corners |
| D6 | chamfer as Scene `Symbol`; new Scene Rect member | `Symbol` | no Scene schema, serializer or adapter change; SVG and TikZ already draw it | a Scene member later |
| D7 | allow pattern on a chamfer; reject | reject with a typed error | a catalogue pattern completes against a Rect; silently dropping the pattern is a design gap hidden behind a conditional | complete a clipped pattern for a polygon (a pattern-owner change) |
| D8 | all four corners; per side | all four | Off-World's tab (two corners cut) needs a side selector, an additive property; the issue asks for a corner shape | add `cellCornerSides` (additive) |
| D9 | extend Typst; document | document | `Symbol` is unsupported for every glyph in Typst today; a polygon path is a separate adapter slice | add a polygon branch to the Typst adapter |

## 6. Architecture review

| Boundary | Result |
| --- | --- |
| View | Unchanged. No new member; unit, count and role stay content. |
| Theme | Two optional role properties in place (additive, Spec 56 section 3.2), admitted in the role contract; invalid values fail with the axis diagnostics. |
| Layout | Owns the outline: ratio to cell size, the per-cell limit and its record, the polygon, identity and paint order. Only the `band` branch changes; with no property the code path emits the same placement. |
| Scene and adapters | No new member. `corner_radius` and `Symbol` outline carry the shape; SVG, resvg and TikZ draw it; Typst draws radius and fails typed for chamfer. |
| Gates | The occlusion gate learns band `Symbol` cells (registry-derived); every other gate already reads bounds, host and paint. Proven by a test that fails if the occluder is dropped. |
| Neighbours | #426 lanes and separators, #880 edge cell, #492 ticks, #493 labels unchanged; the separator and rule paths are not shaped. #585 and #588 files untouched. |

**Findings:** (1) a chamfer carried as `Symbol` silently leaves the occlusion gate unless the gate is changed in the same slice; decided, tested. (2) Pattern plus chamfer would drop the pattern silently; decided, rejected typed. (3) Typst cannot draw a chamfer; disclosed, not hidden. **Risk:** an author who sets a gap of 0 with a large corner sees notches; documented as intended.

## 7. Implementation plan

Four publications: this docs PR; I491-1; I491-2; the acceptance review. Each code PR is `Refs #491`.

**I491-1: declaration, Layout, Scene projection, gate, tests.**
- `schemas/theme-v0.11.schema.yaml`, `schemas/theme-v0.13.schema.yaml` (the two properties beside `cellGap`); run the S0 gate, record it.
- `scene/capabilities.py` (admission, `Symbol` kind for the band role), `layout/surface_axis.py` (band branch: read, validate, outline, reduction record), `layout/surface_quality.py` only if the placement validation needs the `Chamfer` kind, `scene/v05_builder.py` (band projection: `corner_radius`, `Symbol`), `scene/perceptibility.py` (band `Symbol` occluder), `usecases/diagnostic_messages.py` (the new warning text), `docs/specification/39-axis-and-observation-clarity.md` only for corrections.
- Tests: `tests/unit/chrona/presentation/scene/test_axis_cell_corners.py` (built on the `_axis_tiers_scene` helpers used by `test_axis_secondary.py`, fixture font) for geometry, errors, reduction, identity and the default path; a gates test; an adapter test (SVG, resvg PNG pixels, Typst, TikZ); a schema test. **Mutation check** on the ratio, the width limit, each error, the polygon vertices, the occluder condition and the projection.
- Evidence: `tools/regenerate_public_examples.py --check` shows every committed slide byte-identical; conformance; focused and presentation pytest suites; rendered images read.
- Boundary: no example, preset or catalogue Theme, no View schema.

**I491-2: committed slide.** One Theme and View in an existing example folder showing a rounded and a chamfered band tier with a `cellGap` (the slide must show one case from the acceptance row; both are drawn if the slide fits them), the manifest entry and its context; SVG and Scene are bot-generated. Public-evidence counts in the tests that count slides move with it.

**Acceptance review:** `docs/reviews/current/issue-491-axis-cell-corners-acceptance-review-<date>.md` with the `chrona:literal-acceptance/v1` marker and one row per literal criterion, checked by `tools/check_issue_acceptance_reviews.py`, then the three-OS run on the exact commit that publishes it.

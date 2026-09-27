# Design — Group Bands and Headers (#481)

**Status:** proposed for whole-architecture review. **Plan:** [design plan](../planning/active/issue-481-group-bands-and-headers-design-plan-2026-09-26.md). **Evidence:** [prototype evidence](../research/presentation/issue-481-group-bands-and-headers-prototype-evidence-2026-09-26.md). **Authorities:** Specification 45 (Group headers), Specification 49 §3 (semantic registry), Specification 50 §3.4 (Groups and legend), updated by this design.

## Use cases

1. A reader combines a row stripe with a group band across the whole table-and-timeline surface: the stripe traces a row to the timeline's edge, and the group band still marks group structure, whether the band is a solid fill under the stripe, an outline, or a header-only accent.
2. A reader turns on `groups: alternate` and never sees a header that looks like it belongs to the wrong group: a group's band, when painted, includes that group's own header row; a group that is not selected for banding has no header decoration either.
3. A Theme author declares `groupHeader.fontWeight: weight.bold` (or any other declared typography) and sees it on every group-header label, exactly as they already can for every other Theme role.

## Contract 1: row stripes paint above group bands

**Owner: Layout** (`surface_composer.py::compose_surface_layout`). The three background-shape loops — group body bands, group header bands, row stripes — are reordered so groups are appended to the `shapes` list before rows. The renderer already sorts primitives by `(paint_order, original_index)` (`renderers/v05_svg.py:139`); with the emission order reversed, a row stripe and a group band declared at the *same* Theme `backgroundPaintOrder` (the default in every shipped preset) resolve the tie in the stripe's favor, so the stripe paints on top wherever the two opaque fills overlap, and the group's tint remains visible on the rows the stripe skips.

This is the whole fix for "stripes above group bands." It changes no schema, no Theme token, and no `backgroundExtents`/`backgroundDecoration` semantics — an author who wants the reverse order still sets a higher `backgroundPaintOrder` on `row-band` than on `group-band`, which continues to work exactly as `backgroundPaintOrder` already promises.

The other two acceptance techniques need no code change:

- **Outline.** `background_shape` already resolves `backgroundTreatment: outline` to a stroked, unfilled rect (`ShapePlacement` with the role's `treatment`); an unfilled shape cannot occlude anything under it regardless of paint order. A Theme that wants "group bands as outlines" sets `group-band.backgroundTreatment: outline` plus `strokeWidth` and a `.stroke` color binding (the same tokens `calendar-closed` already uses for its own outline).
- **Header-only.** `groupHeaderBand` already paints independent of `backgroundDecoration.groups` whenever a group has a header (`group.header_bounds is not None`); setting `groups: none` with `rows.presentation: header` and `group-band.backgroundTreatment: none` yields a header-only accent with no body fill. Contract 2 below preserves this unconditional behavior for `groups: none` specifically.

**`_validate_background_shapes`** is unaffected: its translucent-overlap check is symmetric over the shape list (any pair, `treatment == "fill"` and `opacity < 1`), not order-sensitive, so no additional validation gap is introduced by an opaque combination.

## Contract 2: a group's band includes its own header

**Owner: Layout** (same function). Two changes, both scoped to the group-building loop and the shape-emission loop:

1. **Geometry.** When a new `GroupPlacement` is started and the group has a header (`group_header_size` nonzero), `content_bounds` is built starting at the header's own block origin, with `block_size` increased by `group_header_size`, instead of starting at the first content row. The header's own `Rect` (`header_bounds`) is unchanged; `content_bounds` now geometrically contains it. This is a pure containment expansion: every existing consumer of `content_bounds` (`_completed_canvas`'s viewport union, the folded-milestone header-expansion replacement) already unions or passes through `header_bounds` independently, so no consumer shrinks or double-counts.
2. **Gating.** The `groupHeaderBand` shape — today unconditional whenever `group.header_bounds is not None` — is emitted only when either `backgroundDecoration.groups == "none"` (preserving the header-only technique, which must remain independent of any body selection) **or** the group is selected by the same `banded` test already used for the body band (`group_decoration == "all"`, or `group_decoration == "alternate"` and the group's alternate turn). Under `all`, every group is selected, so behavior is unchanged from today. Under `alternate`, a group that does not get a body band no longer gets an unconditional header band either — its header carries no decoration, so it cannot be mistaken for the tail of the group before it.

Together, "the group's band" is now a single geometric and selection unit: when a group is banded, its band — one paint, one selection decision — starts at its own header and ends at its own last row; when it is not banded (and `groups` is not `none`), it has no band anywhere, header included.

**Public evidence impact.** Every shipped preset uses `presentation: header` with `groups: all`; the gating change is a no-op for them (every group was already selected). The `content_bounds` geometry change moves the top edge of every painted `groupBand` shape up by `timeline.groupHeader.blockSize` in any preset combining a header presentation with a non-`none` `groupBand` treatment — i.e. every shipped preset except `elevated-light` (which uses no stripes and cards, not a `groupBand` fill, per the issue's own framing) needs its regenerated evidence inspected and the change attributed to this contract, not accepted silently.

## Contract 3: `group-header:*` text uses the `groupHeader` Theme role

**Owner: Layout** (same function) and **Theme** (nine resource files). The group-header `place_text` call's `typography_role` changes from the literal `"text"` to `"groupHeader"`, and its `semantic_id` (currently unset, defaulting to `""`) is set to `"groupHeader"`, matching the table-cell call's existing pattern (`semantic_id=cell.semantic_id`). The baseline offset, currently `body_size` (the `"text"` role's font size), changes to the `groupHeader` role's own font size, so a header with a different declared size still centers correctly in its reserved `timeline.groupHeader.blockSize` band. `docs/specification/49-semantic-presentation-contract.md`'s registry entry for `groupHeader` (`theme_role: groupHeader`) is already published and requires no change; it was simply not honored by Layout.

This requires `groupHeader` — a required typography role once used — to be present in every Theme this contract reaches. It is already declared in `control-room-dark`, `mission-light`, `print-mono`. It must be added, alongside a `groupHeader.fill` color binding (the same pattern as `group-band.fill`/`row-band.fill`), to:

- `src/chrona/resources/presets/bundles/elevated-light/theme.yaml`
- `src/chrona/resources/presets/bundles/executive-light/theme.yaml`
- `examples/aster-ssd/themes/executive-light.yaml`
- `examples/aster-ssd/themes/onboarding-variation.yaml`
- `examples/controller-z-ja/themes/executive-light.yaml`
- `examples/orion-asic/themes/orion-light.yaml`
- `examples/controller-z/themes/executive-light.yaml`
- `examples/controller-z/themes/elevated-light.yaml`
- `examples/controller-z/themes/material-icons-light.yaml`

Each Theme author chooses the declared weight/size for their own design: `elevated-light`/`executive-light` do not currently declare a bold weight token and use group cards rather than bold headers, so their new `groupHeader` role reuses `weight.regular`/`size.body` (no visual change, only an explicit declaration replacing the implicit `text` reuse); the three Themes that already declare `groupHeader` are untouched. No Theme is required to add boldness it did not already choose.

## Why not a silent fallback to `text`

The codebase's Theme contract is closed: a missing required role is a diagnostic (`E_THEME_ROLE_REQUIRED`), never an inferred default (AGENTS.md; Specification 49 §5.1: "a missing required semantic binding fails before rendering"). `groupHeader` is already registered as a required binding for the `groupHeader` semantic; the bug was Layout not requesting it, not the absence of a fallback. Making Layout request the declared role and requiring every Theme it reaches to declare it is the only fix consistent with that contract — a silent `text`-role fallback would hide exactly the authoring gap this issue reports.

## Specification updates (same commit)

- **Specification 45, "Group headers":** state that group-header text is placed in the Theme's `groupHeader` role (not an unnamed "group-header text"), and that a group's band, when selected, includes its own header row.
- **Specification 50 §3.4, "Groups and legend":** add one sentence: a group's header-band decoration follows the same `all`/`alternate` selection as its body band; `groups: none` remains the sole unconditional header-only combination.

## Migration and compatibility

- No View/Layout Profile schema change: `backgroundDecoration.rows/groups` and `reviewSurface.backgroundExtents` keep their existing enums and meaning.
- No Theme schema change: `groupHeader` is already a legal typography role and `*.fill` paint binding shape; nine files gain a value they were missing, using existing token vocabulary.
- **Public evidence:** all three contracts change rendered bytes for most shipped presets (Contract 1 only where a preset is retuned to use both stripes and a `both`-extent group band, which none currently do — so Contract 1 alone changes no shipped preset's output; Contract 2 changes every preset combining `groups: all|alternate` with a header presentation and a non-`none` `groupBand`; Contract 3 changes weight/size on every preset with a `groupHeader` role, and adds text-paint primitives with a new declared role for the nine Theme files gaining one). All 21 public materializers are regenerated in the implementation slices and every changed primitive is attributed to one of the three contracts.

## Diagnostics

No new diagnostic. `E_THEME_ROLE_REQUIRED` on the nine listed Theme files is expected and resolved within the same slice that changes Contract 3's code, not left as a regression.

## Tests

- A combined-surface test: `rows: alternate, groups: all` (or `alternate`), a `groupBand`/`rowBand` extent of `both`, distinct Theme colors for `group-band`/`row-band` — asserts a striped row's Scene primitive paints after (has a higher effective order than) the group band it overlaps, and an unstriped row's only background primitive is the group band.
- A group-header containment test under `groups: all` and under `groups: alternate`: the selected group's `groupBand` shape bounds contain its own `groupHeaderBand` shape bounds; an unselected `alternate` group emits neither shape.
- A `groups: none` + `presentation: header` test: every group still emits a `groupHeaderBand` shape (the header-only technique is unaffected).
- A `groupHeader` weight test: a Theme declaring `groupHeader.fontWeight: weight.bold` (distinct from `text`'s weight) closes a `group-header:*` Scene primitive with that declared weight, not the `text` role's.
- A missing-role test: a Theme without a `groupHeader` role raises `E_THEME_ROLE_REQUIRED` at the group-header placement, not a silent fallback.

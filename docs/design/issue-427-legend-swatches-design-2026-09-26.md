# Design — Legend Swatches and Arrangement (#427)

**Status:** proposed for whole-architecture review. **Plan:** [design plan](../planning/active/issue-427-legend-swatches-design-plan-2026-09-26.md). **Authorities:** Specification 49 §3 (semantic registry), Specification 33 §"legend" slot, Specification 46 (completed scene paint), `src/chrona/presentation/model/semantic_registry.py`.

## Use cases

1. A reader looks at a legend and sees the mark it explains: a milestone key is the same diamond the chart draws, a "Baseline" key that is an outline bar on the chart is an outline bar in the legend, a dependency key is a stroke with the chart's own arrowhead, an "as of" key is the chart's own dash.
2. An author who wants the legend along the bottom of a slide, entries flowing left to right, declares that in the Layout Profile; the entries wrap onto a second line if the slot is too narrow, using the same vocabulary as any other wrapping row.
3. A colour-scale legend entry (`bus`, `payload`, `ait`, …) shows the team's declared title, exactly as a group header already does.

## Contract 1: the swatch is a miniature of its mark

**Owner: Layout constructs geometry; Scene projects it.** The semantic registry (`semantic_registry.py`) already declares one `primitive_kind` per role: `mark` (planned, actual, snapshot, missing-actual, progress-fill, summary-bar, milestone via the `planned`/`actual` point shape), `line` (asOf, dependency, dependency-critical, axis grids), `decoration` (calendar-closed, group/row bands). A legend entry's swatch is constructed and emitted through that same kind's existing machinery, keyed by the entry's own role — not a new per-shape vocabulary:

- **`mark` roles.** Layout calls the same geometry the object marks use: `mark_geometry(role)` for height/offset/corner-radius/paint-order, `progress_track`/`summary_bar_height` where those apply, and — for a point role (milestone) — the same `rounded_diamond_path` used by `place_mark(..., shape="point")` in `layout/surface_composer.py:1150-1166`. The result is a `MarkPlacement`, the exact type real marks already produce (`layout/surface_quality.py:154`), with `placement_id = f"legend-swatch:{role}"`. Scene's existing per-item mark loop (`scene/v05_builder.py:339-396`) chooses `PrimitiveKind.SYMBOL` for a point/open-span shape and `PrimitiveKind.RECT` (with `corner_radius`) for a span; that choice is factored into one helper, `_mark_scene_primitive(mark: MarkPlacement, semantic_id, source_kind, ...)`, called both from the per-item loop and from a new loop over `placed_surface.marks` whose id starts with `legend-swatch:`. A milestone's legend key is therefore the identical `rounded_diamond_path` output as any milestone on that chart, at the identical height (see Contract 2), which is the literal acceptance: "renders as the symbol the Theme binds for milestones, at the size the chart draws it."
- **`line` roles.** Layout builds a `RelationPlacement` (`layout/surface_quality.py:259`) with a short synthetic route (a two-point segment for `asOf`/axis grids, a one-bend elbow with a start/end port for `dependency`/`dependency-critical`, matching a real connector's shape) and the role's own `marker(role)` via `relation_terminals.marker_geometry`. It is appended to `placed_surface.relations` with `relation_id = f"legend-swatch:{role}"`. The existing relation loop (`v05_builder.py:462-470`) already emits every `RelationPlacement` as `PrimitiveKind.PATH` with `marker_start`/`marker_end` and resolves stroke/dash from the role; it needs only to keep excluding `annotation-leader:` and to tag the legend relation with `source_kind="legend"` so the existing scale-swatch paint-override hook (`v05_builder.py:120-121`) continues to apply only where intended. This gives a dependency legend key the chart's own arrowhead, and since `dependency`/`dependency-critical` differ only by `strokeWidth`, the two keys differ by weight alone with no new code, because stroke width is already resolved per role.
- **`decoration` roles.** Layout builds a `ShapePlacement` sized as any background band, and Scene's existing decoration branch (`v05_builder.py:332-338`) resolves `tokens.background(role)` — `fill`, `outline`, or `none` — exactly as it does for a real calendar-closed band. An outline-pattern role (`optional_pattern(role).kind == "outline"`) or a `backgroundTreatment: outline` role therefore renders hollow in the legend for the same reason it renders hollow on the chart: `_paint_family` (`v05_builder.py:61-76`) reads the role's own pattern/treatment, not a legend-specific rule.

No new paint code is needed: `_complete_primitive_paint` already resolves fill, stroke, pattern, dash, and marker from `primitive.visual_role`, and the legend-swatch emission already sets that role to the entry's own role rather than `"legend"` (`v05_builder.py:474-478`, unchanged by this design). This closes acceptance items 1 and 2.

## Contract 2: sizing — block size from the chart, inline size authored

A point mark's on-chart size is one document-wide constant: `role.markHeight × timeline.mark.blockSize`, identical for every milestone in a document regardless of item. The legend reuses that exact product for a `mark`-role swatch's block size (height for a span, side length for a point), and the mark's own `markCornerRadius`/`markOffset`/`progressInset` ratios for its shape — this is "the size the chart draws it" with no new authoring.

A span or line mark's on-chart *length* is per item (a task's duration, a route's geometry) and has no single answer, so the legend needs exactly one new authored value for it. This is the only new Theme surface in this design: a role named `legend-swatch` with one new property, `swatchInlineSize` (a positive length, resolved with the existing `number()` accessor — the same mechanism as `markCornerRadius`). It supplies the inline length for every `span`/`line`/`decoration`-shaped legend entry; `mark`-role point entries (milestone) never consult it, because their bounds are already square from their own geometry. One value, not one per role, because the reference sheets that raised #427 show entries of different roles sharing one visual rhythm along a legend row; an author who wants `Dependency` narrower than `Planned` still can, because `strokeWidth`/`markHeight` differ per role even at the same length.

The swatch-to-label gap is deliberately **not** on this role — see Contract 3 — keeping Theme to visual size/appearance tokens and Layout Profile to placement, per the existing layer boundary.

## Contract 3: Layout Profile arrangement

**Owner: Layout.** The `legend` slot gains, meaningful only when `source: legend`:

- `direction: block | inline` — `block` reproduces today's stacked-downward order (the compatibility default for a migrated v0.9 profile, see Migration); `inline` flows entries left to right.
- `gap: <distance>` — space between adjacent entries and between a swatch and its own label, reusing the exact meaning `gap` already has on a `linear`/`flow`/`grid` container (`schemas/layout-profile-v0.9.schema.yaml:248,267,297`).
- `itemMinInlineSize: <distance>` (optional, `inline` only) — wraps entries onto a new line once the slot cannot fit one more at that minimum, reusing the `flow` container's exact field name and semantics (`layout-profile-v0.9.schema.yaml:283-301`) rather than a legend-only wrap vocabulary.

Layout resolves `legend.bounds.inline_size` against the slot as today; for `direction: inline` it lays swatch+label pairs left to right, wrapping by `itemMinInlineSize` the same way a `flow` container wraps its children, and grows the slot's block size to the number of wrapped lines instead of `legend_step * entry_count`. This closes acceptance item 3.

## Contract 4: scale-entry labels resolve through `entities`

**Owner: content normalization (`review/v05_content.py`).** `scale_entries`' label becomes `project.get("entities", {}).get(value, {}).get("title", value)` — the identical lookup `model/projection.py:208` already performs for a group header — instead of the raw field value. No new field, no schema change: `entities.<id>.title` is already optional and already read elsewhere. This closes acceptance item 5.

## Contract 5: swatch and label take separate Theme roles

The registry's `legendEntry` binding changes `theme_role` from `"legend"` to `"legend-swatch"` (`semantic_registry.py:126`); `legendLabel` keeps `"legend"` (`semantic_registry.py:128`), now exclusively a text role. `theme_role` on `legendEntry` is presently read only for diagnostics/contrast bookkeeping (`color_scheme.py:55`, unused for `legendEntry` today since it carries no `ContrastClass`), so this rename is purely closing the coupling the issue names: no code path resolves a swatch's size, gap, or paint through the label's typography role after Contract 2/3 land, which is what "swatch and label take separate theme roles" asks for. `scaleLegendEntry` is unchanged (`theme_role: "planned"`): a colour-scale key keeps looking like a small planned bar, coloured by the scale, which is already correct. This closes acceptance item 6, and — combined with Contracts 1-4 replacing every fixed constant in `surface_composer` with a role-, Theme-, or Profile-authored value — acceptance item 4.

## Schema versioning

- **Theme.** `theme-v0.11.schema.yaml` (the live authored Theme; `theme-v0.12.schema.yaml` is already taken by the unrelated `derived-theme` kind) gains one new per-role property, `swatchInlineSize`, in a new `theme-v0.13.schema.yaml`. `theme-v0.11` moves to `state: transitioning` with `successor: theme-v0.13.schema.yaml` in `schemas/schema-inventory-v0.1.yaml`; the loader accepts both until a removal slice, matching the pattern already used for every prior Theme bump (v0.5 through v0.11). Adding a role *name* (`legend-swatch`) is not a schema change — role names are open (`propertyNames` pattern, no enum) — only the new property name is.
- **Layout Profile.** `layout-profile-v0.9.schema.yaml` gains `direction`, `gap`, `itemMinInlineSize` on the `slot` node (constrained, by an `if`/`then` on `source: legend`, to apply only to a legend slot) in `layout-profile-v0.10.schema.yaml`. `layout-profile-v0.9` moves to `state: transitioning` with `successor: layout-profile-v0.10.schema.yaml`, following the same v0.3→…→v0.9 pattern already in the inventory.
- **View is unchanged.** Legend content (`legend_entries`, `scale_entries`) is already built entirely from the Detail Profile, Theme, and Project entities; nothing here adds a View field or a new alias, so v0.23 stays reserved for #428/#466/#467.
- **Semantic registry** is not a versioned schema (it is Python, not a public resource); its `legendEntry.theme_role` edit and its existing `primitive_kind` field being put to new use are implementation, covered by the architecture review, not a resource migration.

## Migration and compatibility

- An un-migrated `layout-profile-v0.9` legend slot keeps exactly today's behavior (vertical stack, fixed gap) via the transitional loader; it does not gain the fix until it moves to v0.10. This is a conscious, documented compatibility exception (AGENTS.md discourages retaining compatibility behavior that defeats the design; here it is scoped to *unmigrated* profiles only, exactly like every prior schema bump).
- Every v0.10 legend slot must declare `direction` and `gap` (required by the conditional schema), so a document that adopts the fix cannot leave any legend dimension to `surface_composer` arithmetic.
- Public evidence: `02-programme-board`'s `milestone` legend key changes shape (square → diamond) and size (11.2 px side → `milestone.markHeight × timeline.mark.blockSize`); `planned`/`actual` keys change from a filled square to the role's real bar shape and corner radius. `03-launch-campaign` gains a `legend` slot it does not have today (new primitives, not a byte diff on an existing one). No other committed example currently has a `legend` slot, so no other public SVG changes.
- 14 public Themes need no edit unless their author chooses to set `legend-swatch.swatchInlineSize`; without it Layout raises the existing `E_THEME_ROLE_REQUIRED`/`E_THEME_TOKEN_TYPE` diagnostics the moment a Detail Profile declares a `legend`, exactly like any other missing required role today. Themes that declare a `legend` slot (`wallboard.yaml`, and any new one added in the implementation slice) need one `legend-swatch` role added.

## Diagnostics

No new diagnostic identifier. A missing `legend-swatch` role, or a `legend` slot on a v0.10 profile with no `direction`/`gap`, is already covered by the existing Theme-role and schema-validation diagnostics (`E_THEME_ROLE_REQUIRED`, `E_THEME_TOKEN_TYPE`, JSON-schema validation failure).

## Tests

- A milestone legend entry's primitive kind is `Symbol` with the theme's bound shape, and its bounds equal `role.markHeight × timeline.mark.blockSize` (square), for both a square-diamond and a non-default milestone symbol.
- An outline-pattern role's legend swatch has `fill: none` and the role's stroke; a dashed role's legend swatch carries the role's dash array.
- A `dependency` and a `dependency-critical` legend entry are both `Path` primitives with the role's own `marker_end`, differing only in `strokeWidth`.
- A colour-scale entry's label is the entity's title when `entities.<id>.title` exists, and the raw value when it does not.
- A `legend` slot with `direction: inline` places entries left to right and wraps at `itemMinInlineSize`; `direction: block` reproduces the current stacked order.
- A v0.9 legend slot (no `direction`/`gap`) still renders with today's fixed arithmetic; a v0.10 legend slot without `direction` or `gap` fails schema validation.
- `swatchInlineSize` absent on a Theme that declares a `legend` slot raises `E_THEME_ROLE_REQUIRED` at the same point a missing `markHeight` would.

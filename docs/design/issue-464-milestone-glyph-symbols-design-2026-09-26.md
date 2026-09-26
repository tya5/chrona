# Design — Milestone Glyph Symbols (#464)

**Status:** proposed for whole-architecture review. **Plan:** [design plan](../planning/active/issue-464-milestone-glyph-symbols-design-plan-2026-09-26.md). **Authorities:** Specification 07 §5.2 (amended below), Specification 08 §5.2/5.3 (amended below), Specification 64 (adjacent icon capability, not reused directly).

## Use cases

1. A Theme author replaces every gate's built-in diamond with a bowling pin, a paper lantern, a hexagon, a star, a treasure chest, or a flat-pack circle — one glyph asset, chosen once, applied by rule to every milestone with that role.
2. A pin or lantern needs more than one colour (a white body, red neck stripes; a vermilion body, dark caps and rib lines). Both render from one Theme value, and each part's colour is either the milestone's own role colour or a colour fixed in the asset.
3. A viewer distinguishes a planned gate from its baseline ghost, and a treasure-chest gate from its ghost baseline, without relying on colour — for a colour-blind viewer or a monochrome print.
4. An author keeps writing dependency arrows the same way; they still stop exactly at the gate's edge, whatever shape the gate now has.

## Contract 1: a Theme value can be a multi-part glyph

**Owner: Theme (schema), resolved through the existing `symbol` token type.** `schemas/theme-v0.11.schema.yaml`'s `symbol` value schema gains a second shape, additive to the existing `if/then` on `type: symbol`:

```yaml
oneOf:
  - {type: object, additionalProperties: false, required: [shape], properties: {shape: {const: diamond}}}   # existing 4, unchanged
  - type: object
    additionalProperties: false
    required: [shape, viewBox, parts]
    properties:
      shape: {const: glyph}
      viewBox:
        type: array
        items: {type: number, exclusiveMinimum: 0}
        minItems: 2
        maxItems: 2
      parts:
        type: array
        minItems: 1
        items:
          type: object
          additionalProperties: false
          required: [d, paint]
          properties:
            d: {type: string, minLength: 1}
            paint: {enum: [fill, stroke, none]}
            color: {type: string, pattern: "^#[0-9A-Fa-f]{6}$"}
```

- `viewBox: [width, height]` is the glyph's own local coordinate box; `d` is ordinary SVG path data in that box, in paint order (first part paints first).
- `paint: fill|stroke|none` says which of the role's own paint channels colours this part when no literal `color` is declared. `none` paints nothing (reserved for a future guide/construction path; no target uses it).
- `color`, when present, is this part's fixed colour, independent of the milestone's planned/actual colour — for Tenth Frame's red neck stripes, which stay red whether the gate is planned or actual.
- `shape: diamond|circle|square|chevron` is unchanged; this is purely additive, so every one of the 22 existing public Themes (which only ever declare the four built-in shapes) validates unchanged.

**Why extend `symbol` rather than add a token type.** The role property (`roles.<role>.symbol: <name>`) and the resolution entry point (`ThemeTokenView.symbol`) are already exactly "name a symbol value for this role." A new token type would duplicate that plumbing for no reason; the built-in/glyph distinction is a property of the *value*, not of how a role refers to it.

## Contract 2: three independently bindable roles, not one role read three ways

**Owner: Theme (roles), Scene builder (resolution).** Today every call site resolves `ThemeTokenView.symbol()` with the implicit default role `"milestoneSymbol"`. This design adds two new registered role properties, `milestoneSymbolActual` and `milestoneSymbolBaseline`, both optional:

```python
def symbol(self, role: str = "milestoneSymbol") -> Mapping[str, Any]:
    ...  # unchanged signature; now returns the full value mapping, not just shape (Contract 4)

def variant_symbol(self, variant: str) -> Mapping[str, Any]:
    """variant in {'planned', 'actual', 'baseline'}; falls back to milestoneSymbol."""
    role = {"planned": "milestoneSymbol", "actual": "milestoneSymbolActual",
            "baseline": "milestoneSymbolBaseline"}[variant]
    return self.symbol(role) if role == "milestoneSymbol" or self.has_role(role) else self.symbol("milestoneSymbol")
```

`scene/v05_builder.py`'s five call sites pass the correct `variant` instead of calling `symbol()` bare: the two "planned" sites (including the folded-group one) pass `"planned"`; the "actual" sites (open-span and point, including folded) pass `"actual"`; wherever a `snapshot`/baseline purpose resolves a symbol (there is none today, because baseline reuses the planned/actual shape — see Contract 5) passes `"baseline"`.

This lets Pixel Quest bind an entirely different asset (a ghost sprite) to `milestoneSymbolBaseline`, and lets Tenth Frame/Yuya/Title Card/Sunday Strip leave `milestoneSymbolActual`/`milestoneSymbolBaseline` unset and inherit the one pin/lantern/hexagon/star asset for every variant — satisfying literal bullet 1 exactly ("bind `milestoneSymbol` (and its actual and baseline counterparts)").

The Theme role registry (spec 07 §5.2's applicability contract) gains these two role names as valid `symbol`-typed properties; an unset one is not an error, matching every other optional role property already in the schema.

## Contract 3: per-part paint, resolved once in Scene construction

**Owner: Scene (`scene/v05_builder.py`, `scene/mark_geometry.py`).** The existing `_paint_family`/`resolve_scene_paint` pipeline already decides, from the resolved semantic role's Theme tokens, whether that role paints **filled** (`PaintFamily.SOLID`) or **outline-only** (`PaintFamily.OUTLINE`, when the role declares `pattern: {kind: outline}`) — this is not new. What is new is applying that per-role decision to every part of a glyph, plus a literal per-part override:

For a resolved role paint `role_paint` (the same `ScenePaint` any other primitive with this role would get) and a glyph value's parts:

- **If the role resolved to `OUTLINE`** (baseline's usual treatment): every part is drawn stroke-only, with `role_paint.stroke`/`strokeWidth`/`dash`/`opacity`, **regardless of the part's own `paint`/`color`**. A literal fill colour never leaks into an outline-mode variant. This is the mechanism behind literal bullet 3 for the five targets that keep one asset across variants: baseline is drawn as every part's own outline, dashed, in the role's own (typically grey/muted) stroke colour — not filled, not the same colour as planned/actual, and legible in monochrome.
- **If the role resolved to `SOLID`** (planned/actual's usual treatment): each part is drawn according to its own `paint`:
  - `paint: "fill"` → `fill = part.color if part declares one else role_paint.fill`, `stroke = None`.
  - `paint: "stroke"` → `stroke = part.color if part declares one else role_paint.stroke`, `strokeWidth = role_paint.stroke_width`, `fill = None`. (No per-part stroke width in the schema; parts share the role's stroke width, kept minimal because no target needs a second width.)
  - `paint: "none"` → the part is omitted (no primitive emitted for it).
  - `opacity` is always `role_paint.opacity` for every part; dash is empty for a filled part (dash only applies when a part strokes).
- A role that declares neither `pattern: outline` nor any fill/stroke override behaves exactly as it does today for a non-glyph symbol.

**Where the colour ultimately comes from is documented, closing literal bullet 2's "the choice is documented":** a part paints from the Theme role unless the asset fixes that part's colour with `color`, and any part's fixed colour is suppressed whenever the role is in outline mode. This is stated in Specification 07 (amendment below) and repeated in the Theme authoring value's own schema comment.

## Contract 4: one glyph, several sibling `Symbol` primitives

**Owner: Scene (`scene/model.py`, `scene/mark_geometry.py`, `scene/v05_builder.py`).** `SymbolGeometry` gains an optional field:

```python
@dataclass(frozen=True)
class SymbolGeometry:
    outline: tuple[PathCommand, ...]           # unchanged: overall silhouette, built-in shapes always set only this
    parts: tuple[GlyphPart, ...] = ()           # new: non-empty only for shape: glyph

@dataclass(frozen=True)
class GlyphPart:
    commands: tuple[tuple[str, tuple[tuple[float, float], ...]], ...]  # same shape as SceneIconPath.commands, supports cubic
    fill: str | None
    stroke: str | None
    stroke_width: float | None
    dash: tuple[float, ...]
    opacity: float
```

`mark_geometry.symbol_geometry` gains a branch for `shape == "glyph"`: it computes one **contain, centred** affine transform from `viewBox` into the milestone's existing `bounds` (unchanged Layout box — Layout does not know a glyph is inside it), reuses `chrona.presentation.icons.normalizer`'s path tokenizer (its `_path`/`M/L/H/V/Q/C/Z` grammar, made a shared helper rather than duplicated) to parse each part's `d` into normalizer command tuples, and maps every point through the transform. `outline` is set to the *first* part's transformed path (the glyph's principal silhouette — used only for the pre-existing clip-host code path, which is not exercised by any of the six targets; a multi-part clip host is called out as a known gap below, not solved).

`scene/v05_builder.py`'s emission for a point-source mark, at each of its five call sites, changes from *emit one `Symbol` primitive* to: resolve the variant's glyph value; if `shape != "glyph"`, emit one `Symbol` exactly as today; if `shape == "glyph"`, emit **one sibling `Symbol` primitive per surviving part** (after the `paint: "none"` omission), each with:
- the same `scene_id` prefix plus a `:part{n}` suffix (unique, stable, and reconstructable from part order — no new identity scheme);
- the same `source_ref`, `source_kind`, `purpose`, `visual_role`, `bounds`, `slot_id`, `href`, `link_title`, `end_treatment`;
- a strictly increasing `paint_order` within the glyph (part 0 first), so a later part visibly stacks over an earlier one;
- `symbol=SymbolGeometry(outline=<part 0's path only, kept on every sibling for schema validity>, parts=())` — each sibling primitive carries **its own single part's geometry**, not the whole glyph's `parts` list. (Rationale below.)

**Why one part per primitive, not one primitive with a `parts` list.** This reuses `_complete_primitive_paint` verbatim — the *existing* mechanism (role → `ScenePaint`) already runs per primitive, so per-part paint (Contract 3) needs no new nested-paint Scene concept, no schema-level `parts`-of-paints structure, and no adapter branch beyond "loop the sibling primitives, each already fully painted." The only Scene-model change under this shape is that `SymbolGeometry` briefly (during Scene construction, before `_complete_primitive_paint`) carries the *unpainted* geometry for its one part; by the time a primitive reaches `_complete_surface_paint`, it is an ordinary single-outline `Symbol` with one resolved `ScenePaint`, indistinguishable in shape from today's diamond except that several of them share `sourceRef`/`purpose`. **Net Scene wire-format change:** none beyond what Contract 3's colours already produce — `schemas/scene-v0.6.schema.yaml`'s `symbol` definition and `primitive` definition are unchanged; a glyph is just several ordinary `Symbol` primitives. This is deliberately the smallest contract that meets literal bullets 1–3.

`SymbolGeometry.parts`/`GlyphPart` shown above exist only as Scene-**builder**-internal intermediate types inside `mark_geometry.py`, used to plan the sibling primitives before paint is resolved — they are not fields of `ScenePrimitive` and are never serialized. `scene/model.py`'s `SymbolGeometry` is unchanged (still just `outline`); each sibling primitive gets an ordinary single-outline `SymbolGeometry` for its own part. This is stated explicitly because the alternative (one primitive, a serialized `parts`-of-paints list) was considered and rejected: it would need a new nested Scene paint shape, a new schema definition, and a new adapter branch, none of which buys anything the sibling-primitive shape doesn't already get from existing machinery.

**Precedent this follows:** a planned span today already emits several primitives from one object (bar, label, comparison mark); several `Symbol` primitives sharing `purpose="planned"` for one gate is the same pattern, at finer grain.

## Contract 5: baseline reuses the same mechanism, not a special case

Because Contract 3's outline-mode rule already forces every part to stroke-only using the role's own colour and dash, **no separate "baseline glyph" logic is needed** for the five targets that keep one asset: `milestoneSymbolBaseline` is left unset, falls back to `milestoneSymbol` (Contract 2), and the `snapshot`/baseline semantic role's own Theme binding (already `pattern: outline` + `dash` for every other snapshot-purposed mark today) makes every part draw as a dashed outline automatically. Pixel Quest's ghost sprite is the one target that needs a genuinely different asset, and Contract 2's independent role binding covers it without adding a second mechanism.

## Contract 6: dependency ports keep using the bounding box; the constraint is on the asset, not on Layout

**Owner: unchanged — `layout/ports.py`, `layout/relation_terminals.py`.** No code changes. Layout continues to compute a connector's port at the milestone `MarkPlacement.bounds` edge, exactly as it does for the four built-in shapes, all of which already touch every edge of their own bounding box.

**The corresponding constraint, made explicit:** a glyph's `viewBox` aspect ratio SHOULD match the milestone mark's block/inline aspect ratio (today effectively square, since diamond/circle/square/chevron are all drawn full-bleed in a roughly square box) closely enough that the contain-fit glyph touches the box's left/right edges at the port's row — i.e. the artwork should be drawn full-bleed in its own `viewBox`, with no internal padding, exactly as all six approved targets' hand-drawn art already is. All six committed READMEs draw their gate glyph filling its cell; this is verified, not assumed, when the committed slide is built. A future glyph authored with internal padding or a markedly different aspect ratio would have its port land on empty canvas next to the visible artwork — a real, named limitation, not silently absorbed. Solving it precisely (computing the glyph's *painted* horizontal extent from its parts for the port) is deferred: it would require Layout to parse and transform path data during placement, a materially larger change than six targets' full-bleed art needs, and is named here for the lead/owner to confirm rather than done quietly.

## Contract 7: contrast checking follows paint order onto a Symbol, not only a Rect

**Owner: Scene (`scene/contrast_policy.py::_ground_under`).** The prior-primitive kind filter in `_ground_under` (`if prior.get("kind") != "Rect": continue`) becomes `if prior.get("kind") not in {"Rect", "Symbol"}: continue`. Everything else in `_ground_under` (paint-order/index ordering, bounds containment, opacity/gradient handling) is unchanged and already generic. Consequence: a glyph's second part is checked for contrast against the *first part's* resolved fill (its true visual ground), and only the first part (and any part painted before any Rect) falls through to the canvas — matching what a viewer actually sees, and directly answering the issue's "the perceptibility and contrast gates measure the glyph's effective paint against the surface beneath it, as they do for the diamond" for a glyph with more than one paint layer.

**Expected impact on the 22 existing public slides: none.** No existing `Symbol` primitive today has another primitive painted over it at the same bounds (a diamond is one paint layer), so this candidate set only grows for the *new* multi-part case; verified by the implementation slice's batch diff, not assumed here.

`scene/perceptibility.py::_occlusion_findings` needs no change: it only ever compares `Text` against `Rect`, so sibling `Symbol` parts sharing bounds never trip it, and multi-part glyphs pass the perceptibility gate the same way single-part symbols do (checked directly on the committed slide's evidence, literal bullet 4/5).

## Migration and compatibility

- **Schema:** `schemas/theme-v0.11.schema.yaml`'s `symbol` value schema gains the `glyph` shape, additive (`oneOf` alongside the unchanged 4-shape object). No Theme version bump — this is a new legal *value*, not a new token *type* or role *property* shape.
- **Scene:** no wire-format change (Contract 4). `schemas/scene-v0.6.schema.yaml` is untouched. No version bump, matching the precedent of every other additive field landed under `chrona/scene/v0.6` (`endTreatment`, `contrastTreatment`, `hostPlacementId`, the table fields — confirmed by `git log` on the schema file).
- **Theme roles:** `milestoneSymbolActual`, `milestoneSymbolBaseline` are new optional role properties. Every existing Theme (22 public slides across the presets and examples) declares only `milestoneSymbol`; both fall back to it, so no existing Theme file changes and no public byte is expected to change from Contracts 1–5 alone. Contract 7's `_ground_under` widening is the only change with a (verified-empty) blast radius on existing evidence.
- **No new diagnostic code.** An invalid `parts`/`viewBox`/`color` shape is caught by the existing `E_THEME_SCHEMA` (schema-level) and `E_THEME_TOKEN_TYPE` (`mark_geometry.py`'s runtime checks, extended for the new shape) paths — the same two-layer guard the repro exercised for the rejected `pin` string.

## Specification amendments (same commit)

- **Specification 07 §5.2 (Tokens):** state that a `symbol` value may be a built-in shape or a multi-part glyph (`viewBox` + `parts`, each part painted from the role or a literal asset colour), that a role's outline-mode paint treatment overrides every part's colour, and that `milestoneSymbolActual`/`milestoneSymbolBaseline` are optional roles falling back to `milestoneSymbol`.
- **Specification 08 §5.3 (Public-surface primitive closure):** correct the stale "`Symbol` carries a closed `shape` identifier" sentence to state that a `Symbol` primitive carries one completed outline and paint, that one semantic gate may be represented by several sibling `Symbol` primitives sharing `sourceRef`/`purpose` when its shape is a multi-part glyph, and that contrast/perceptibility evaluation treats a prior `Symbol` as possible ground for a later primitive at the same bounds.

## Open risks named for the lead/owner

1. **Port-at-visual-edge (Contract 6)** is met by an authoring constraint (full-bleed `viewBox`), not by Layout computing the glyph's true painted extent. Every approved target satisfies it today; a future glyph with internal padding would not, and nothing enforces the constraint at load time. Flagged rather than solved, because enforcing or computing it exactly is a materially larger Layout change than any of the six targets requires.
2. **Clip-source onto a multi-part glyph** is not solved (only the first part is available as `outline`). No committed slide needs it; a future icon-overlay-on-a-glyph-gate combination would need this revisited.
3. **Icon-catalog-backed glyph parts** (the issue body's "It can be a vector path or a catalogue icon") are not implemented; only inline `d` path data is. Left as a named follow-up per the design-plan's scope boundary.

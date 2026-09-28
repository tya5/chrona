#496 — Theme asset catalogues: current work record

## Published baseline and design plan

Base `main`: `bbe6734f`. The issue is open with no later comments. Spec 64's
v0.3 icon catalogue already provides pinned `set:name` closure and one
catalog-level SPDX licence/notice. #464 supplies inline Theme glyphs, #465
reuses catalogue PNG for annotation containers, Scene has finite pattern
geometry, and #479 provides preset detail profiles. The builtin preset
library does not copy catalogues. Spec 62 packages remain proposed. #454
orders #505 and #466 before this mechanism; design can proceed while product
changes wait for their merged bases.

Literal issue acceptance:

1. “A catalogue can hold `glyph` and `pattern` entries, validated and normalized with licence and notice.”
2. “A Theme can bind a catalogue glyph as a milestone or gate shape, reusing #464's glyph path, and a pattern as a role's fill. SVG and PNG render them identically, and the perceptibility and contrast gates see their effective paint.”
3. “A builtin preset can declare catalogues and a detail profile. `chrona preset copy` copies them with notices, and `chrona render --preset` uses them with no extra flags.”
4. “A builtin starter catalogue ships the glyphs and patterns listed above. At least one builtin preset uses a glyph and a pattern, and at least one ships a legend through its detail profile.”
5. “A missing asset reference fails with a Theme pointer and the `set:name`.”

Use cases: locally import licensed declarative glyph/pattern assets once;
bind them through Theme without copying geometry into every Theme; copy a
builtin preset with all catalogue and legend resources; render that preset
without extra flags; fail a stale/missing Theme asset reference before Layout.
Inventory dependencies against Specs 07/08/62/64 and the current icon
catalogue, Theme token, Layout glyph, Scene pattern/paint, SVG→resvg PNG,
perceptibility/contrast, preset copy and Context closure paths.

Decide before implementation: a strict successor catalogue schema and
normalization/identity for glyphs and closed pattern tiles; YAML import and
licence/notice provenance; `set:name` resolution and exact Theme pointers;
which existing Theme role fills accept tiles; Scene-completed pattern ink and
substrate as the common SVG/PNG/contrast authority; and the atomic builtin
catalogue/preset/detail distribution boundary. The source SVG-subset importer
is optional in the issue and can be deferred; no raw SVG reaches rendering.
Vector container art and unimplemented Presentation Package acquisition are
not prerequisites, but today's licensed PNG container path must remain intact.

Design slices: (1) catalogue model/identity and source import; (2) Theme
binding and completed Scene/adapter/contrast delivery; (3) preset closure,
copy and builtin assets; (4) acceptance evidence. The next publishable unit
is the selected design, normative spec update and whole-architecture review.
No product file changes before a separately published implementation plan.

## Selected design and architecture review

Normative contracts are in [Specification 64](../../specification/64-portable-icon-catalogs.md), [Specification 07](../../specification/07-style-and-theme.md), [Specification 08](../../specification/08-scene-and-rendering.md), and [Specification 62](../../specification/62-declarative-presentation-packages.md). This section records the issue-specific selection and whole-architecture review.

### Decisions

1. Keep the existing `icon-catalog` resource kind and Context `iconCatalogs` closure, advancing its contract to `chrona/icon-catalog/v0.4`. The immutable licensed catalogue adds closed `glyph` and `pattern` entries beside `icon`; existing icons and #465 PNG artwork remain available after explicit migration. v0.3 is not silently reinterpreted. `set:name`, catalogue identity, aliases, duplicate checks, pinning, and notices remain the shared discipline. No Context fields change; the closure resolver must admit and identity-check v0.4.
2. Glyph entries are normalized multi-part path data with a positive viewport, ordered parts, and `fill|stroke` paint modes. They carry no fixed colours; the Theme milestone/gate role supplies paint. Theme v0.13 adds `shape: {catalog: set:name}` while retaining the existing inline glyph form for migration; derived inherited Theme advances from v0.12 to v0.14. Resolved parts enter #464's mark-fit path; Layout completes the mark geometry.
3. Pattern entries are normalized tiles, sides 1–256 units, with at most 64 ordered filled circles/rectangles, lines, and arcs. Arc input is lowered to quadratic segments at maximum 0.001 tile-unit deviation; raw arcs do not survive import. Tile angle is finite degrees in `[0,360)` clockwise about tile center. Density is integer 1–100, validated as the rounded percent of covered samples on a deterministic 128×128 center-point grid over the tile. Entries carry no colors or target syntax. A Theme role's existing `pattern` property names a typed pattern token whose value is `{kind: catalog, ref: set:name}`. Theme `fill` is the opaque substrate and Theme `stroke` is opaque ink. Catalog pattern tokens are admitted only for these existing role/property consumers: `planned.pattern`, `actual.pattern`, `snapshot.pattern`, `scenario.pattern`, `missing-actual.pattern`, `network-node.pattern`, `milestone.pattern`, `progress-fill.pattern`, `summary-bar.pattern`, `annotation-callout-box.pattern`, `annotation-highlight-box.pattern`, `annotation-note-box.pattern`, `annotation-arrow-box.pattern`, `axis-band-decoration.pattern`, `axis-band-decoration2.pattern`, `as-of-label-chip.pattern`, `member-label-chip.pattern`, and `finish-delta-chip.pattern`. No other role/property pair accepts catalogue patterns.
4. The coordinator resolves and validates references after Theme inheritance and before Layout. Layout owns repeated-region bounds, clipping, and tile origin; Scene v0.7 carries normalized tile primitives, declared angle/density, `paint.fill=substrate`, `paint.stroke=ink`, completed clip bounds, and origin. Adapters may encode periodic repetition in native syntax but cannot change tile/angle/origin/clip. PNG uses the pinned SVG-to-resvg route. Contrast checks substrate vs actual host and ink vs both substrate and host; the minimum pairwise ratio must meet the role floor (3.0:1 for marks, 1.10:1 for decorations). Perceptibility inspection receives these same two channels plus geometry, angle, density, and bounds. All channels are opaque under current ground rules. No adapter invents a fallback.
5. One declarative YAML ingress defines glyph/pattern entries, with explicit SPDX and notice inputs. Complete input validation precedes atomic canonical output. An SVG-subset importer is deferred. Raw SVG, CSS, filters, gradients, arbitrary artwork, network retrieval, and new raster routes remain excluded. Existing #465 PNG container entries retain current scope.
6. Keep `presentation-preset/v0.1`: it already pins optional `iconCatalogs` and detail profiles. `preset-library/v0.2` adds catalogue members. Copy writes exact catalogue bytes and notices under `catalogs/` and includes the references in the generated preset. `render --preset` consumes that closure without extra flags. The #470 project-generic bundle boundary and explicit preset selection remain; Theme auto-discovery and the bare-render default do not change.
7. One package-owned starter catalogue carries the seven requested glyphs and six pattern entries: halftone dots, seigaiha, ordered-dither at 12.5%, 25%, and 50%, and dense hatch. At least one existing generic preset references it, uses a glyph and pattern, and supplies a legend through its review-detail profile. No Presentation Package resolver is introduced: Spec 62 admits the approved catalogue as an ordinary pinned static asset member only when that separate implementation resumes.

### Responsibility, diagnostics, and migration

The authoring boundary resolves `set:name` and reports unknown set/name, unsupported kind, malformed entry, duplicate namespace, or missing notice before Layout. A missing Theme asset is `E_THEME_ASSET_REFERENCE` at the exact Theme declaration pointer and includes the authored `set:name`; preset closure mismatch names its catalogue member path. Import validates all input before atomically replacing output. Copy refuses nonempty output and copies only declared members. Preset/context closure verifies exact catalogue and asset identities; there is no directory scan or network fetch.

Scene pattern values contain no Theme references, set names, source YAML, or uncompleted transform. Adapters receive the same finite geometry and resolved paint for SVG and PNG; they do not resolve catalogues, choose variants, measure, clip, or select fallbacks. Layout and Scene preserve the icon's meaningful/decorative and textual-equivalence rules; a glyph is mark shape, not a separate semantic signal.

Whole-architecture consistency: Specs 07/26 preserve View/Style semantic selection and Theme appearance; Spec 64 preserves local-only ingress and exact closure. Specs 08/46 keep completed Scene paint and renderer-neutral geometry; this tile contract fills a current geometry gap without moving placement into Scene. Specs 33/50 retain bounds, repetition, clipping, and placement in Layout. Specs 63 and ADR-0018 retain explicit target support; this slice admits only SVG and the resvg-derived PNG route. Specs 55/58, #470, and Spec 28 preserve project-generic presets, evidence separation, and legend ownership. Spec 62 remains proposed and gains no resolver or registry behavior here.

Migration is explicit: catalogue v0.3 to v0.4 and preset-library v0.1 to v0.2 require rewrite; Theme v0.11/v0.12 remain valid and the new authored/derived contracts are v0.13/v0.14; Scene pattern data requires v0.7 (current v0.6 is unchanged). No compatibility bridge silently drops assets. Inline Theme glyphs and existing flat fills remain valid, and #465 PNG payloads and Theme insets preserve bytes and meaning.

Design is complete for implementation planning. Normalization contract is `chrona/theme-asset-normalization/v0.1`: glyph viewport sides are integers 1–4096, each glyph has 1–32 paths, and each normalized path is at most 65,536 characters; each pattern has a 1–256-unit tile, 1–64 ordered primitives, angle, and grid-validated density. Coordinates are finite and tile-local; import rejects rather than clips or repairs. Open implementation evidence is builtin source provenance/notices and SVG/PNG byte-equivalence fixtures. This publication contains no product implementation or implementation plan.

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

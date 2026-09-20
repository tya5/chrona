# Layout Expression Engine

**Status:** Design complete  
**Owns:** M19–M22 declarative composition and its integration with existing presentation layers.

## 1. Unified ownership

This specification replaces the M15 table-timeline profile as the composition authority.
It does not replace View, Style, Theme, Scene, or Render Context:

| Existing layer | Retained authority | Layout Profile may do |
|---|---|---|
| View | fact selection, grouping, order, window, comparison and logical annotation anchor | choose a declared View slot only |
| Style | semantic fact to role mapping | assign only role prominence, never select facts |
| Theme | concrete token values | bind layout token references, never geometry policy |
| Render Context | target, locale, as-of date, viewport | supply environment; no hidden current date |
| Layout Profile | composition constraints and slot hierarchy | arrange existing projection primitives |
| Scene / Output | resolved primitives and target capabilities | emit derived geometry/diagnostics only |

`table-timeline-profile/v0.1` is therefore deprecated as an implementation-prototype
profile. Its `table`, `axis`, `groups`, and `routing` fields migrate respectively to
`slots.table`, `slots.timeline`, `slots.groups`, and `constraints.connectors` in the
Layout Profile. The old profile cannot be combined with a Layout Profile.

## 2. Grammar and solver

A Layout Profile is a closed declarative resource. It defines a canvas, named regions,
tracks, gaps, and named slots. Regions use `stack`, `grid`, `split`, `overlay`, or
`anchor`; split/grid tracks are `fraction`, `content`, or bounded `minmax` values.
Slots consume only a declared projection surface: `title`, `table`, `timeline`,
`summary`, `legend`, `annotations`, or `notes`. A slot can state alignment, priority,
overflow policy, and role reference.

The deterministic solver allocates canvas → regions → slots → primitives. It never
stores resolved coordinates as resource state. Constraints are solved in source order
after stable-ID tie breaking. Over-constrained tracks, unavailable sources, overlap,
unroutable connector, clipping of required accessible text, and missing target capability
are diagnostics. No renderer fallback may hide them.

## 3. Controlled expression

Designers can alter aspect ratio, margins, density, hierarchy, grouping surface,
table-header treatment, axis level/label density, panel placement, connector avoidance,
and role prominence. They cannot use scripts, SVG fragments, arbitrary formatters,
unanchored absolute coordinates, Project-title selectors, or preset-ID conditions.

The closed formatter catalog is `plain`, `date`, `signed-days`, `percent`, and
`status-text`; values and missing treatment still originate in View. Theme tokens follow
the DTCG-compatible token boundary where types overlap, but Theme remains Chrona's
versioned authority until an explicit import/export adapter is added.

## 4. AI and preset contract

Human and AI designers create the same View/Style/Theme/Layout Profile resources. An AI
proposal is validated against an explicit immutable closure and produces a Layout
Manifest (resource identities/content hashes, slot-source mapping, resolved regions, and
diagnostics). It cannot propose executable code or direct Scene edits. Presets may inherit
resources but rendering must never branch on a preset ID.

## 5. Scene, accessibility, and output

The closed primitives remain those in Specification 08 §5. `layoutRegion`,
`layoutSlot`, `tableHeader`, `tableCell`, `axisBand`, `groupSurface`, `summaryPanel`, and
`routedConnector` are purpose/metadata families on those primitives; each has
source/derived provenance, role, text alternative, and region/slot ID. SVG requires `layoutManifest`,
`tableSemantics`, `hierarchicalAxis`, and existing accessibility/source capabilities.
Logical reading order is slot order, not paint order. Colour is never the sole state cue.

## 6. Acceptance invariants

Design successor: `29-schema-owned-presentation-settings.md` owns the v0.2
externalization contract and the migration of prototype `surface` settings. It
removes duplicate typography/dimension authority and named-region code defaults.
This is a design-only successor; v0.1 runtime support remains unchanged.

- Same closure plus profile yields byte-identical Layout Manifest and SVG.
- A layout change cannot alter schedule, Actual, grouping membership, or comparison value.
- Two profiles may differ materially while reusing the same View/Style/Theme facts.
- Invalid/overflow/collision cases diagnose before an artifact can be claimed complete.
- A preset authored by a human and an AI proposal traverse the same schema and solver.

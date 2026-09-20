# Layout and Expression Engine Plan — 2026-09-19

**Status:** Design complete — implementation is not started.
**Purpose:** Let human designers and AI designers compose a high-quality Chrona review
surface without making a renderer, a generated image, or an AI-produced coordinate map
the source of truth.

## 1. Product decision

Chrona needs a declarative **Layout Profile** between the semantic View Projection and
Scene. It is not a fixed template catalog. A designer may build reusable presets, but
the engine interprets the same resource grammar for every profile.

```text
Project + Schedule + Actual + View   = selected facts
Style + Theme                        = visual language
Layout Profile + Render Context      = composition constraints
Scene                                = resolved, source-linked primitives
SVG                                  = derived artifact
```

The profile may control composition and visual hierarchy; it may not select unexposed
facts, alter Project/Schedule/Actual, execute code, use a local clock, or persist
resolved pixel coordinates as authoritative data.

## 2. Declarative freedom

| Concern | Designer-customizable declaration | Semantic owner remains |
|---|---|---|
| Canvas | aspect ratio, safe margins, density, background role | Render Context / Theme |
| Regions | named grid regions, tracks, gaps, min/max sizing, overflow policy | Layout Profile |
| Surface order | title, table, timeline, legend, summary, note-list slots | Layout Profile |
| Table | column width strategy, header treatment, row rhythm, alignment, value formatter from a closed catalog | View + Layout Profile |
| Timeline | axis levels, label density, guide strength, today/as-of marker | View window + Layout Profile + Render Context |
| Grouping | header/band/separator, span across regions, group spacing, optional derived aggregate slots | View grouping + Layout Profile |
| Emphasis | role-based prominence, label placement, milestone treatment, callout priority | Style/Theme + Layout Profile |
| Connectors | routing policy, avoidance regions, collision fallback | Layout Profile / Scene |

Freeform absolute coordinates are intentionally excluded from v0.1. Designers receive
constraint-based latitude rather than fragile pixel blobs: grid, stack, overlay, anchor,
min/max, alignment, and priority. A later opt-in overlay layer may permit bounded
presentation annotations anchored to semantic scene IDs, but never unanchored schedule
geometry.

## 3. Required layout-profile vocabulary

The first schema must define a closed, versioned grammar:

```yaml
version: chrona/layout-profile/v0.1
canvas: {aspectRatio: '16:9', margin: spacious, density: presentation}
regions:
  - {id: header, area: header, layout: stack}
  - {id: schedule, area: main, layout: split, tracks: [table: 38%, timeline: 62%]}
  - {id: evidence, area: footer, layout: grid, columns: 2}
slots:
  table: {region: schedule.table, header: filled, rowRhythm: relaxed}
  timeline: {region: schedule.timeline, axis: [quarter, month, week], asOf: visible}
  summary: {region: evidence, placement: cards}
constraints: {overflow: diagnose, connectors: obstacle-aware, text: ellipsize-with-source}
```

Every percentage, token, slot, and anchor has deterministic validation. Over-constrained
regions, unavailable slots, clipped semantic labels, overlap, unsupported target
capability, and unresolved token values are diagnostics—not silent renderer choices.

## 4. AI-designer boundary

An AI designer may propose a Layout Profile, View, Style, and Theme as ordinary,
reviewable resources. It must not emit Python, SVG fragments, arbitrary expressions, or
direct Scene mutations. Host validation resolves a proposal against an explicit Project,
View, target, and Render Context; accepted resources are versioned and reproducible like
any user-authored preset.

Evaluation should report a `LayoutManifest`: profile IDs/content hashes, resolved
regions, overflow/collision diagnostics, and source-to-slot mapping. This lets a human
review why an image differs without treating pixels as truth.

## 5. Delivery order

| Milestone | Design and implementation slice | Exit evidence |
|---|---|---|
| M19 — Layout grammar | Owning specification, schema, validation rules, fixtures, Scene/Output connection review. | Two materially different user-defined profiles validate; invalid overlap/overflow cases diagnose. |
| M20 — Constraint layout runtime | Deterministic region/track solver; table/timeline/summary slots; layout manifest. | Repeated output identity; no hard-coded profile branches; source-linked layout assertions. |
| M21 — Expressive review primitives | Calendar bands, table hierarchy, milestone/callout/connector placement, bounded formatter catalog. | Light executive acceptance sample reaches required hierarchy without semantic mutation. |
| M22 — Designer workflow and release | Preset inheritance, AI proposal validation path, visual regression/gallery, accessibility and reuse release review. | Human and AI-authored profiles share identical validation/output path. |

## 6. Immediate remediation before M19

The current M15–M18 adapter must be reclassified as a prototype against this plan: its
fixed dimensions and colours, incomplete axis levels, missing connector/annotation
rendering, and summary/title collision prove that a Layout Profile is absent. Do not add
further per-example branches. M19 design closes this gap before M20 implementation.

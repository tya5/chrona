# Declarative Layout Systems Research — 2026-09-20

**Status:** Complete research input for M24; non-normative.

## 1. Question

Which established layout ideas let Chrona authors state intent instead of tuning
coordinates, offsets, and unrelated numeric limits?

The comparison is deliberately split by problem. No surveyed system is a complete fit:
Vega-Lite specializes in visualization composition, CSS in box layout, ConstraintLayout
in sibling relationships, Graphviz in graphs, and Cassowary in general linear
constraints.

## 2. Comparison

| System | Strong idea | Chrona decision |
|---|---|---|
| Vega-Lite | `hconcat`, `vconcat`, wrappable `concat`, layering, facets, shared/independent guides, content-aware size | Adopt composition as a small closed algebra. Do not let Layout facet Project facts; View must first expose repeated presentation sources. |
| CSS Grid | `fr`, intrinsic tracks, `minmax`, `fit-content`, named areas, gap | Adopt proportional/intrinsic/bounded sizing and named nodes. Avoid CSS cascade and implicit-placement complexity. |
| CSS Flexbox / Box Alignment | main/cross axes, item/content alignment, distribution, baseline and safe overflow | Adopt logical inline/block axes, two-axis placement, distribution and first/last baseline. Use deterministic `safe` fallback or a diagnostic, never silent loss. |
| Android ConstraintLayout | parent/sibling anchors, center from opposing constraints, guidelines, content-derived barriers | Adopt a bounded anchor vocabulary for overlay children. Exclude arbitrary equations and unrestricted priorities. |
| Flutter | constraints flow down, measured sizes flow up, parent chooses position | Adopt an explicit measure then arrange pipeline. A child cannot choose an authoritative global coordinate. |
| Graphviz | direction/rank/separation and automatic routing | Retain for connector/rank inspiration only. It is not the page-layout grammar. |
| Cassowary / Auto Layout | required and preferred equalities/inequalities, incremental solution | Do not adopt in M24. General strengths and equations would make YAML hard to review and introduce ambiguous solutions. Reconsider only with use cases the closed grammar cannot express. |

Primary references:

- [Vega-Lite view composition](https://vega.github.io/vega-lite/docs/concat.html)
- [Vega-Lite facet](https://vega.github.io/vega-lite/docs/facet.html)
- [Vega-Lite sizing](https://vega.github.io/vega-lite/docs/size.html)
- [CSS Grid Layout Level 2](https://www.w3.org/TR/css-grid-2/)
- [CSS Box Alignment Level 3](https://www.w3.org/TR/css-align-3/)
- [Android ConstraintLayout](https://developer.android.com/develop/ui/views/layout/constraint-layout)
- [Flutter constraint model](https://docs.flutter.dev/ui/layout/constraints)
- [Graphviz graph attributes](https://graphviz.org/doc/info/attrs.html)
- [Cassowary linear arithmetic constraint solver](https://constraints.cs.washington.edu/solvers/cassowary-tochi.pdf)

## 3. User-task analysis

| Task | Required primitive | Numeric input normally needed? |
|---|---|---|
| Center a title in the page or header | slot `place.inline: center` | No |
| Vertically center text in a measured band | `place.block: center` | No |
| Align several text labels by their first baseline | `alignItems: first-baseline` | No |
| Put table and timeline in a 3:7 relationship | row plus `fr` sizing | Ratio only; no coordinates |
| Size a legend to its measured content | `content` | No |
| Keep a panel at least content-sized but allow growth | `minmax(content, fill)` | No |
| Distribute cards evenly | `space-between/around/evenly` | No |
| Put a note after the timeline edge | overlay anchor plus token gap | Token name only |
| Put a value after the widest label | end barrier over label node IDs | No |
| Reflow panels when the viewport narrows | `flow` plus tokenized minimum item size | Token name or deliberate bound |
| Reuse organization spacing and page structure | Theme token references and `extends` | No repeated numbers |
| Fine optical correction | explicit fixed distance escape hatch | Yes, reviewed as intentional |

## 4. Rejected alternatives

### Keep adding fields to Presentation Settings

Rejected. The complete settings aggregate is useful after resolution but makes authors
edit internal detail, repeats values, and encourages array replacement. It also leaves
composition split between a Layout Profile and `settings.layout`.

### Expose x/y or arbitrary offset expressions

Rejected. They solve a screenshot, not a reusable layout. They are fragile under text,
locale, font metrics, viewport, and content changes.

### Expose a general constraint solver immediately

Rejected. Required/preferred strengths, under-constrained systems, competing optima, and
floating-point stability would become public semantics before Chrona has a demonstrated
need. Named anchors, guides, barriers and tree containers cover the identified tasks.

### Copy Vega-Lite facet directly

Rejected. Faceting partitions data and therefore touches View authority. Layout may
arrange a repeated source already declared by View, but may not choose the field or
facts used to create it.

## 5. Design consequences

1. One author-facing Layout Profile replaces both the prototype profile and the
   layout-authoring portion of complete Presentation Settings.
2. Layout is a tree. Normal flow uses row/column/grid/flow; free relative placement is
   limited to overlay children in one coordinate space.
3. Every node has a stable ID. Inheritance overrides nodes by ID, not by array index.
4. Distances are either Theme number-token references or deliberate non-negative fixed
   values. Examples and built-in profiles use tokens.
5. Measurement is a declared input. `content` never guesses font metrics.
6. Resolution is multi-pass and deterministic; cycles and ambiguity are errors rather
   than solver-selected surprises.


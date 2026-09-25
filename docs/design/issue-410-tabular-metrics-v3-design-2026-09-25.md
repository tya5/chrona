# Design — #410 I410-2 Tabular Metrics v3

**Design plan:** `84e2c7d2`.

## Decision

Numeric figure spacing is a measured face capability, not a browser, SVG, or
typesetter preference.  Chrona will replace `declared-metrics-v2` with
`declared-metrics-v3` and `chrona/font-metrics/v2` with
`chrona/font-metrics/v3`.  Every selected face carries two complete ASCII-digit
advance maps: `proportional` and `tabular`.

`FontMetrics.width()` receives the already-resolved finite numeric spacing and
uses the corresponding map for U+0030 through U+0039.  Other glyphs continue
to use the face's ordinary advances.  A tabular selection is valid only when
all ten tabular advances are positive and equal.  Both maps must contain every
ASCII digit.  No caller may infer that default cmap advances represent either
feature.

## Metrics payload and import

The v3 payload retains face identity, units, vertical metrics, and ordinary
glyph advances, and adds:

```yaml
version: chrona/font-metrics/v3
numericAdvances:
  proportional: {'48': 584, '49': 441, ...}
  tabular: {'48': 572, '49': 572, ...}
```

The importer obtains each map from the selected OpenType feature lookup for
`pnum` or `tnum`; if a feature has no substitution for a digit, its current
glyph is the result for that feature.  This handles Noto Sans correctly:
default glyphs are equal-width tabular digits and `pnum` supplies proportional
substitutions.  The importer rejects a missing digit, non-positive advance, or
non-uniform tabular map.  It writes a new metrics resource identity; it never
guesses a feature from an adapter or host font.

## Context and resource migration

`render-context/v0.16` is the only live Context contract and requires
`declared-metrics-v3`.  Every public Context and packaged descriptor migrates
atomically to v3 metric resources.  The v0.15/v2 pair becomes transitioning
only; resource dispatch accepts no compatibility reader.  v3 resources receive
new package addresses and content identities so their provenance is explicit.

## Semantic numeric selection

`signedDays` is already a finite View content format.  Normalization assigns
such a table cell the semantic text role `numeric`; all other table cells use
`text`.  `TableCellContent` carries that role to Layout.  Headers remain
`text`.  Generic table allocation receives a Layout measurement callback, so
each header or cell is measured with its own completed treatment rather than a
single table-wide font assumption.

The HALCYON Themes define `numeric` with body typography and
`numericSpacing: tabular`.  A Theme without that role rejects only when a View
actually materializes a `signedDays` cell.  The role is semantic, not a
per-column adapter option: View says what the value is, Theme says how numbers
are treated, and Layout combines those facts.

## Projection and output

`TextPlacement` and `TextLayout` already transport numeric spacing.  I410-2
makes it an explicit public completed value for both modes.  SVG emits exactly
`font-variant-numeric="proportional-nums"` or `tabular-nums`; Typst and TikZ
receive their respective completed feature syntax.  Adapters do not calculate
advances, inspect font tables, or choose a default.

Every nonnumeric run remains explicitly proportional.  Thus its Layout width
and target feature agree even for faces whose default glyphs are tabular.

## Exclusions

* No monospace face, host font, or arbitrary OpenType feature string is added.
* No View property selects a font feature directly.
* No kerning/shaping engine, locale-specific figures, or numeric transformation
  is introduced.
* Text orientation and system-font resolution remain I412-1 and I411-1.

## Required evidence

1. importer and resolver fixtures prove Noto proportional and tabular maps;
   malformed/missing/nonuniform maps reject.
2. Layout tests prove signed values, wrapping, ellipsis, and cell alignment use
   the selected map.
3. a HALCYON signed-days column has tabular Scene/SVG/typeset evidence;
   ordinary text has proportional evidence.
4. regenerated Context, metrics, Scene, and SVG corpus evidence is reviewed;
   full test, conformance, structural, package, and three-platform gates pass.

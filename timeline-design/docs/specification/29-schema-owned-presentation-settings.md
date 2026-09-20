# Schema-Owned Presentation Settings v0.2

**Status: Design contract. Runtime not implemented.**

Resolved Theme, Layout, Detail, and Context are bound once into the Scene Builder's
`ResolvedPresentationInput`. SVG and other adapters read only completed Scene
primitives, token values, and the manifest. Re-resolving settings, supplying missing
values, or recalculating dates, slots, fonts, lanes, or routes in an adapter creates
duplicate authority.

## 1. Purpose and scope

Move every design choice left in rendering code into declarative data. Scope includes
all public output paths in `gantt_surface.py`, `layout.py`, `review_svg.py` (including
legacy review, summary, and formatting helpers), and `render.py` (legacy minimal SVG).
Migrating only the current Gantt while leaving fixed values in old paths is incomplete.

The source of truth is each owner `$defs` in
`presentation-settings-v0.2.schema.json`. The fixed-value inventory is
`../planning/presentation-fixed-value-inventory-v0.2.json`; each entry records code
origin, destination, type, representative value, and removal policy. Its 78 groups
include fourteen font roles, thirteen color roles, and six line roles. JSON artifacts
validate the same data model as YAML; authors may use YAML.

"Every" means every design choice. Day differences, calendars, endpoint and
accessibility meaning, XML escaping, array indices, center-coordinate division by two,
and normalized shape vertices are invariant calculations, not design values. Settings
MUST NOT change meaning or safety.

## 2. Single ownership and integration with existing design

| Owner | Authoritative settings | Consolidation / removal |
|---|---|---|
| View | Fact sources for selection, order, grouping, visible period, and columns | Unchanged; do not copy into Layout |
| Style | Mapping facts to semantic roles | Unchanged; add no numeric values or wording |
| Theme | Color, opacity, typeface, size, weight, line height, letter spacing, stroke width/dash, radius, symbol size, pattern | Consolidate `surface.fontSize/titleSize/groupFontSize/barHeight` and adapter fallbacks |
| Layout | Regions, tracks, margins, alignment, row height, column allocation, axis-band height, bar gaps, obstacle clearance, route scoring, legend flow | Remove name-based header/footer and density branches, fixed rectangles, and manual baselines |
| Detail (`28`) | Legends, explanations, missing-data wording, accessible descriptions, formatting, summary display names | Consolidate `surface.groupLabel` and hard-coded English strings |
| Render Context | Actual viewport dimensions, locale, and fixed font-measurement resources | Remove canvas-ratio-to-dimensions dictionaries; prohibit duplicate dimension sources |
| Output | SVG coordinate precision, font-output policy, overflow-conformance policy | Remove fixed adapter precision and implicit clipping |

The outer `presentation-settings` object is an aggregate for validation and fixtures,
not a new owner. Place `$defs/theme|layout|detail|context|output` in `settings` inside
the existing resource's v0.2 body. Never write one setting into multiple bodies. Do not
change View/Style semantic schemas or Project/Actual/Summary fact schemas.

Legacy Render Context `viewport` / `evaluation.locale` and new settings cannot coexist;
migration moves them once. Consolidate legacy `layoutMetrics` references into
`context.fontMetrics`. Preserve unrelated Context values such as `asOfDate` and
revision references.

Existing Theme token→role resolution remains the stage before normalization to this
concrete-value contract. Validate token aliases, cycles, and types, then produce
complete Theme settings with no unresolved token strings. Layout distances belong only
to Layout. Diagnose a Style-generated role unsupported by Theme. `groupPaints` keys are
stable IDs; do not branch on group count, title, or sample name.

## 3. Defaults, overrides, and compatibility

Defaults live in a **complete YAML preset** fixed by version and content hash. Schema
`default` is not runtime injection. Renderer recovery through
`get(..., number/color/wording)` is prohibited; every resolved field is required.
Inheritance is fixed base, then user override only. Objects merge by key, arrays replace
wholly, null cannot delete, unknown fields error, and base cycles error.

The authoring schema is `presentation-preset-v0.2.schema.json`. It accepts exactly one
of complete settings or a fixed-base reference with partial overrides; array elements
must be complete. `presentation-preset-override-v0.2.yaml` overrides Japanese labels,
radius, text, spacing, and route scoring. It is an author-facing aggregate distributed
to owning resources after resolution. Current default fixtures are design examples and
their font-asset identities are illustrative. Do not claim render readiness until
implementation binds real measurement assets.

v0.1 remains unchanged; v0.2 is explicit migration and opt-in only. Retaining legacy
`surface` values simultaneously yields `E_PRESENTATION_DUPLICATE_AUTHORITY`.
Legacy-value destinations:

- `fontSize` → Theme typography body/tableHeader/month; `titleSize` → heading;
  `groupFontSize` → group; `barHeight` → plannedHeight/actualHeight.
- `groupMode/fraction/gap` → Layout group; `axisLevels` → Layout axis levels.
- `barGap` → Layout bars gap; `showVariance` → Layout variance visibility.
- Planned/Actual band composition → Layout `bars.comparisonMode`; never infer stacked.
- `groupLabel` → Detail groupLabel; fixed legacy legend → Detail legend.
- Canvas `aspectRatio` → preset with explicit Context viewport dimensions. Expand
  margin/density names during migration; never branch on them at runtime.
- Remove legacy minimum widths 920/960 and data-count canvas expansion. The migration
  adapter accepts explicit Context viewport and diagnoses overflow. A compatibility
  preset preserves v0.1 call shape but does not promise pixel-compatible auto-growth.
- Diagnose simultaneous legacy canvas dimensions and a different explicit legacy
  Context viewport; do not choose silently. Expand name-based header/footer dimensions
  into region blocks.

Finally, consolidate legacy paths through compatibility adapters into the same resolved
settings→Scene→SVG path. Do not preserve known output defects for pixel compatibility;
record intentional changes in review.

### 3.1 Closed v0.1 compatibility-adapter contract (P4 remediation)

v0.1 View, Theme, and Layout Profile cannot reproducibly determine the v0.2 Render
Context's required `fontMetrics.contentIdentity` and viewport. An adapter MUST NOT
silently complete v0.2 from process font selection, canvas auto-growth, or code defaults.

A compatibility adapter accepts exactly one of:

1. The caller supplies version/hash-bound `presentation-settings/v0.2` or a Preset,
   which is resolved and passed to the v0.2 renderer.
2. The caller explicitly selects the legacy renderer as a **diagnostic legacy
   adapter**. It is outside v0.2 completion and reproducibility guarantees and records
   `legacyPresentation: v0.1` plus `E_PRESENTATION_LEGACY_ADAPTER` in the output
   manifest. Mixing with v0.2 settings is prohibited.

For now, existing CLI v0.1 calls normalize to option 2; callers requiring v0.2 quality
migrate to option 1. Do not implement automatic generation of a fully v0.2-compatible
Preset from v0.1 until migration input includes content-addressed real metrics assets.
This prevents filling missing values with appearance defaults.

## 4. Closing measurement and placement

Replace `.58` width estimation, `.34` baseline estimation, and fixed text widths
112/60/57 with **measurement from fixed font metrics**, not new tuning knobs.
`context.fontMetrics.assets` is the complete tuple
`{family, weight, revision, contentIdentity, path}`. `path` is relative to an explicitly
supplied asset root, rejects traversal, and identifies a canonical
`chrona/font-metrics/v1` JSON table. The table contains family, weight, units-per-em,
ascent, descent, default advance, and Unicode-codepoint advances. Its exact bytes,
family, and weight must match the declaration. Host family discovery such as `fc-match`
and direct host font-file opening are prohibited in the reproducible path. For every
Theme typography weight,
select only a matching declared asset, in font-stack order. Never substitute regular
for bold. An undeclared family/weight, identity mismatch, or absent asset yields
`E_FONT_METRICS_UNAVAILABLE`. `missingFont: declared-fallback` permits only moving to
the next **declared** family, never a process default or neighboring weight. Derive the
baseline from asset ascent/descent and Theme line height, and reuse one measurement for
wrapping, overflow, obstacle checks, and SVG. Include measurement asset, selected
family/weight, and locale-asset identities in the manifest.

A region block is fixed, fraction, or content, with min/max; its name has no meaning.
After fixed/content resolution, divide the remainder by fraction weights. Content is
measured intrinsic bounds. In addition to resolved settings, the solver explicitly
receives `intrinsicBlocks[regionId]` and
`intrinsicTracks[regionId][trackIndex]`, computed once during the same Scene build.
Never use content `value` as fallback or estimate; missing intrinsic input yields
`E_LAYOUT_REQUIRED_OVERFLOW`. Diagnose cyclic content dependencies, min>max, and
negative remainder without hidden shrinking.

A slot explicitly names region and track index. Diagnose multiple occupants on a track
unless it is an overlay. Table and timeline share one row grid. Allocate columns equally
only when `columnTracks` is empty. View sets visible time; scale padding adds drawing
space, not time. `layout.scale.singlePointSpanDays` may set a single-point display span
without changing the semantic date. The Scene Builder measures axes and row-local
TextLayout in this display window. If required axis labels, item labels, or point symbols
do not fit, emit `E_LAYOUT_REQUIRED_OVERFLOW:text`; an adapter MUST NOT locally widen
the window. The standard base explicitly uses seven days, the minimum Date-only week.
Other preset spans must pass the same measurement and overflow checks.

A legend is a flow of measured swatch, label, and gap; remove per-string widths such as
150/145/220. Summary and notes use the same measurement flow. As text/data grows, wrap
or follow explicit overflow rules; do not invent an external panel.

`bendPenalty`, `clearance`, `portOffset`, and `gridOffset` are declarable route-scoring
inputs. Compute ports from shape, and preserve original relation for endpoint types
start/end/at. Include arrow dimensions, strokes, and text regions in obstacle checks.
Stable tie breaking and search limits are versioned safe algorithm contracts; arbitrary
code and unbounded search are prohibited.

## 5. Wording, formatting, and accessibility

Templates allow only strings and replacement of registered `{identifier}` values.
Common identifiers are `windowStart`, `windowLastVisible`, `selectedCount`,
`unmatchedCount`, and `missingCount`. Only title additionally allows `title`;
unmatchedActual allows `unmatchedIds`; summaryEntry allows `label/value`; coverageRatio
allows `actualCount`. Join unmatched IDs with `listSeparator`. A zero Summary
denominator uses `formatting.unknown`. Title cannot be empty. Format Summary values by
semantic date/number type before replacement; remove the legacy behavior that formats
every integer as variance days. Expressions, attribute access, functions, HTML/SVG,
and eval are forbidden; always escape replacement output. Changing missing-data or
summary display names changes neither missingness meaning nor denominator.

Generate month names, quarters, and dates from a closed formatter enum plus explicit
locale. Compute `windowLastVisible` from a documented date-window-end display contract.
Delegate DateTime/DST calculation to existing Core; do not redefine it with Date logic.

The month catalog is `short-month-year`, `long-month-year`, `numeric-year-month`,
`short-month`, `long-month`, and `numeric-month`. The quarter catalog is
`quarter-year`, `year-quarter`, and `quarter`. Axis levels additionally include `year`,
whose closed label is the four-digit year. Scene construction applies these formats;
SVG adapters serialize the completed label and never call `strftime` to choose another
spelling.

Point and arrow shape enums are behavioral contracts. Scene Symbols retain the resolved
point shape and adapters support diamond, circle, and square from identical bounds.
Dependency and explanatory paths retain the resolved marker shape; `none` emits no
marker reference. Every facet paint applies both `color` and `opacity`. Bar planned and
Actual heights are independent properties and must remain independently observable.

Detail legend from Specification 28 is the sole legend source of truth. Layout owns
placement only and Theme owns swatches only. Group details, supplier observations, and
milestone digest remain low-priority and unimplemented. Any future panel uses common
text/paint/layout without reintroducing fixed values. Removing a role from the legend
does not remove required semantic explanation from aria/description/text. Reject empty
accessible descriptions, removed provenance metadata, and meaningless clipping.

## 6. Validation boundary and diagnostics

Schema validates types, unknown fields, enums, positive dimensions, opacity, and finite
limits. Limits define safe input ranges, not current appearance defaults.
The planned semantic-closure validator checks:

- Resource version/hash, base cycles, unresolved tokens, and duplicate owners.
- Unique region IDs, slot references, track indices/bounds, and axis level/height match.
- Marker inset below width, radius within bar bounds, and reachable clearance/ports.
- Unregistered template identifiers, duplicate roles, and missing required explanations.
- Font-measurement assets, locale assets, and output capabilities.
- Required viewport regions and collisions involving text, arrowheads, variance, and
  missing-data labels.

Representative diagnostics are `E_PRESENTATION_SETTINGS_REQUIRED`,
`E_PRESENTATION_DUPLICATE_AUTHORITY`, `E_PRESENTATION_REFERENCE`,
`E_PRESENTATION_TEMPLATE`, `E_FONT_METRICS_UNAVAILABLE`,
`E_LAYOUT_REQUIRED_OVERFLOW`, `E_CONNECTOR_UNROUTABLE`, and
`E_OUTPUT_CAPABILITY_MISSING`. Schema success alone does not guarantee semantic
closure or rendering quality.

## 7. Completion conditions

Every inventory row for every public SVG path is classified as externalized,
measurement-derived, or invariant. Renderers read only resolved settings and never
recover unspecified values. YAML-only acceptance examples change theme, language,
spacing, text, symbols, legend order/wording, axes, and routing tendency. Equal
closure/metrics/locale/output versions produce byte-identical SVG. Validate reference
Gantt images plus long Japanese text, extensive missing data, long legends, and varied
viewports. The current 104 tests are a baseline, not proof of new implementation.

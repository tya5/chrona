# Semantic presentation contract for Issue #49

## Decision

A presentation surface is constructed in four closed stages:

```
authoring input → ingress adapter → PresentationContract → LayoutPlacement → SceneSurface
                                      ↘ ThemeContract ↗          ↘ Materializer evidence
```

No later stage may reinterpret raw authoring spelling, infer an undeclared semantic role, or select a theme fallback.

Geometry-free temporal facet selection belongs to the presentation model and
is shared by original Style fact collection and Layout composition. It does
not measure, clip, place or route: those decisions remain Layout-owned.

## 1. PresentationContract

`PresentationContract` is an immutable, typed model built once after schema validation. It contains only canonical semantics:

- `TableContract(columns, cells)`
- `RowContract(rows, members, groups, tracks)`
- `TimeContract(axis, axisBands, calendarClosure, asOf)`
- `DecorationContract(groupHeaders, legend, annotations, notes, summaries)`
- `RelationContract(endpoints)`

Each entry has a canonical `semantic_id`, a source owner, and a required Scene purpose. Raw field names and theme token names are not stored.

### Invariants

1. A canonical semantic id is unique within its scope.
2. A member identity is `rowId:itemId` whenever View projects explicit rows; it is never re-derived by Scene.
3. An `asOf` fact comes only from Actual; calendar closure comes only from Project; View only selects their presentation.
4. A table column has one measured origin and width before text primitives are emitted.
5. A legend entry and a primitive role are declared from the same semantic registry entry. From #427, a legend entry's swatch is dispatched by that entry's own registry `primitive_kind` (`mark`, `line`, or `decoration`), not by a legend-specific shape.
6. A missing required semantic binding fails before rendering.

## 2. Ingress adapter

`normalize_presentation_input` is the only compatibility boundary. It accepts public supported aliases and returns canonical contract fields.

| Accepted input | Canonical contract value | Downstream visibility |
| --- | --- | --- |
| `showMemberLabels: true` | `labels.enabled = true` | none |
| `labelPlacement: plot` | `labels.placement = plot` | none |
| `asOf` | `time.as_of` | none |
| `as-of` theme alias | canonical semantic `asOf` binding | none |

Aliases are normalized once and are prohibited in Layout, Scene, renderer, materializer, and tests. The deleted Settings/Theme contract remains deleted: this adapter receives the current public View/Actual inputs only.

## 3. Semantic registry and theme contract

The host-owned `chrona/semantic-vocabulary/v0.1` resource is the sole binding
authority (#419 V1). Its `body.bindings` is an ordered list of `semanticId`,
`primitiveFamily`, `purpose`, `sceneRole`, `themeRole` and nullable
`contrastClass` records. Families are `mark`, `line`, `decoration`, `label`,
and `icon`; these are semantic families, not adapter primitive kinds. The
Python registry validates this resource and derives immutable lookup indexes;
it does not retain a parallel binding table. Existing consumers continue to
own required-role activation, primitive completion and materializer checks.

The installed resource has kind `semantic-vocabulary` and id `chrona-core`.
Duplicate semantic IDs, malformed records, unsupported versions, absent bytes
or mismatched identity fail before a usable registry or Scene is produced.
Normal and Draft closure record the exact same vocabulary content identity;
the render checks that the closed vocabulary is the host lookup authority.
This is not an authored Context override or package registration extension.
The initial117 records retain all prior values and declaration order. The
selected examples below are explanatory; the packaged resource is exhaustive.

| Semantic id | Primitive | Scene purpose | Canonical theme binding |
| --- | --- | --- | --- |
| `planned` | Rect/Symbol | `planned` | `planned` |
| `actual` | Rect/Symbol | `actual` | `actual` |
| `asOf` | Path/Text | `as-of`, `as-of-label` | `asOf` |
| `deadlineMark` | Path | `deadline-mark` | `deadline-mark` (contrast class `mark`; the role is required when a View shows deadlines) |
| `deadlineMarkOutline` | Rect | `deadline-outline` | `background` (completed opaque ground under the deadline stroke, not independently contrast-classified; Spec07 outlineWidth) |
| `deadlineCaption` | Text | `deadline-caption` | `deadline-caption` when it binds fill, otherwise the explicit `text` alternative; ground text at4.5:1. Typography follows Spec07. |
| `groupHeader` | Rect/Text | `group-header-band`, `group-header` | `groupHeader` |
| `slotHeading` | Text | `slot-heading` | `slot-heading` (ground text; the role is opt-in and the `text` role applies without it, #1064) |
| `titleText` / `subtitleText` | Text | `title-text` / `subtitle-text` | `heading` / `subtitle` when the respective role binds `fill`, otherwise the explicit registered `text` alternative; ground text (#1164) |
| `kickerText` | Text | `kicker-text` | `kicker` when it binds `fill`, otherwise the registered `text` alternative; ground text (#1189) |
| `summaryCaption` / `summaryUnit` | Text | `summary-caption` / `summary-unit` | `summary-caption` / `summary-unit`; ground text, explicitly carried by inline summary placements (#1190) |
| `networkLabel` | Text | `title-text` (existing public network-label purpose) | `text`; Layout distinguishes node labels from `titleText`, so title ink never repaints them (#1164) |
| `regionFrame` | Rect | `region-frame` | Layout completes `region-frame` or the declared `region-frame-<paint>`; an absent selected role omits only that frame (#1165) |
| `groupTab` | Rect | `group-tab` | `group-tab` (contrast class `decoration`; the role is opt-in, #882) |
| `calendarClosed` | Rect | `calendar-closed` | `calendarClosed` |
| `periodBand` | Rect | `period-band` | `period-band` |
| `periodLabel` | Text | `period-label` | `period-label` (state text: the Theme declares `contrastTreatment`; the role is opt-in) |
| `periodLabelChip` | Rect | `label-chip` | `period-label-chip` |
| `axisBand` | Text | `axis-band` | `axis` |
| `legendEntry` | dispatched by the entry's own role `primitive_kind` (Rect, Symbol, or Path) | `legend-swatch` | entry's own role, sized against `legend-swatch.swatchInlineSize` (#427); `swatchGap`, `swatchBlockSize` and `pointSwatchSize` (#1111). A state-text role on this graphical swatch is classified as mark, with no text treatment (Spec46 §8, #1515). |
| `legendLabel` | Text | `legend-label` | `legend` (painted in `legend` when the Theme binds `legend.fill`, else `text`; ground text, #1062) |
| `annotation` | Rect/Text/Path | `annotation-*` | `annotation` |

The renderer keeps stable primitive role strings where needed for public Scene compatibility (for example `as-of`). They are declared by the registry rather than handwritten in composition. Theme lookup accepts explicitly declared ingress aliases only and resolves to the canonical binding before Scene construction.

The registered `heading`, `subtitle`, `kicker`, `summary-caption` and
`summary-unit` inks are general Theme text roles, not purpose-only contrast
classes: a View using one for a table cell retains
purpose-based ground-text classification. State-text role precedence and the
purpose restrictions of other registered Scene roles remain unchanged.

## 4. LayoutPlacement handoff

Layout owns measurement and geometry. It produces immutable `LayoutPlacement` records:

- table column origins and widths;
- row/group/header bounds;
- mark tracks and mark bounds;
- axis intervals and label slots;
- decoration slots and annotation rails;
- relation obstacle geometry.

Scene owns semantic-to-primitive emission only. Scene may select a primitive's z-order and content from `PresentationContract`, but may not calculate column width, row height, track allocation, endpoint identity, or label-fit geometry.

For realized legend selection (#1679), the pure presentation model supplies
one shared, geometry-free key-relevant paint result: effective channels,
override precedence, gradient token identity and selected-profile admission.
The existing use-case/pipeline adapter supplies neutral capability support and
optional-omission flag from the selected profile to both consumers; Layout
does not import Scene's `VisualProfile`. The shared result carries effective
channels, admitted gradient identity or its omission, and the existing
diagnostic identity/pointer on failure, not Scene primitives or coordinates.
Layout consumes it with completed positive, clipped-visible placements to
select keys; Scene consumes the same result while assembling paint. Extract
the relevant existing channel/gradient admission rules, do not introduce a
second resolver or import Scene types into Layout. Actual variance applies
only under the existing unoverridden Actual/non-outline branch; Style and
explicit paint-role precedence remain unchanged. A replaced gradient neither
participates in identity nor reports an omission. An omitted optional gradient
leaves the emitted solid ink as witness; a required capability still fails.
Scene retains bounds-dependent gradient/effect construction and adapter-ready
paint assembly. Finite key shapes use the shared ink projection defined in
Specification 28; they do not inherit source effects.

After final route/label selection, Layout recomposes legend entries once in
the conservatively reserved slot. No legend-driven row, route or annotation
retry is introduced. Comparison-source absence is normalized before measuring
the table (Specification 06), never in Scene or adapters.

## 5. Verification closure

`assert_presentation_contract` validates, before materialization:

1. every enabled contract semantic has a registry entry;
2. every required registry binding is present in the resolved theme;
3. every required placement exists and is non-overlapping where applicable;
4. emitted Scene primitives cover each enabled registry purpose;
5. each example manifest selects its declared context and public materializer output reproduces byte-for-byte.

Realized-key tests additionally cover paint-result parity between Layout and
Scene, semantic-family/paint deduplication, positive progress, encoded versus
unencoded planned witnesses, absent versus supplied-empty comparison sources,
and actual adapter PNGs. A declaration or Scene-only count is not proof of a
visible matching key.

Tests are organized by contract boundary:

- normalization tests: aliases become canonical values once;
- registry tests: enabled semantic ↔ theme binding ↔ required purposes;
- layout tests: placement invariants only;
- Scene tests: declared purpose coverage from placements;
- materializer tests: all contexts and generated evidence only.

## Migration

Implement incrementally behind the existing public build entry point:

1. introduce the immutable contract and registry with adapters that reproduce current inputs;
2. move table, row/track, axis, and decoration geometry to `LayoutPlacement`;
3. replace direct raw-input and literal-role reads in the Scene builder;
4. migrate tests to contract-level assertions; and
5. regenerate all evidence exclusively with the public materializer.

No generated SVG is edited by hand. No legacy Settings/Theme code is restored.

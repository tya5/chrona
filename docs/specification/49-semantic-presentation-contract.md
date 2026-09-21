# Semantic presentation contract for Issue #49

## Decision

A presentation surface is constructed in four closed stages:

```
authoring input → ingress adapter → PresentationContract → LayoutPlacement → SceneSurface
                                      ↘ ThemeContract ↗          ↘ Materializer evidence
```

No later stage may reinterpret raw authoring spelling, infer an undeclared semantic role, or select a theme fallback.

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
5. A legend entry and a primitive role are declared from the same semantic registry entry.
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

The registry owns canonical primitive semantics. Its entries declare `semantic_id`, primitive kind, Scene purpose, canonical theme binding, whether a binding is required, and materializer evidence requirement.

| Semantic id | Primitive | Scene purpose | Canonical theme binding |
| --- | --- | --- | --- |
| `planned` | Rect/Symbol | `planned` | `planned` |
| `actual` | Rect/Symbol | `actual` | `actual` |
| `asOf` | Path/Text | `as-of`, `as-of-label` | `asOf` |
| `groupHeader` | Rect/Text | `group-header-band`, `group-header` | `groupHeader` |
| `calendarClosed` | Rect | `calendar-closed` | `calendarClosed` |
| `axisBand` | Text | `axis-band` | `axis` |
| `legendEntry` | Rect/Text | `legend-swatch`, `legend-label` | entry role |
| `annotation` | Rect/Text/Path | `annotation-*` | `annotation` |

The renderer keeps stable primitive role strings where needed for public Scene compatibility (for example `as-of`). They are declared by the registry rather than handwritten in composition. Theme lookup accepts explicitly declared ingress aliases only and resolves to the canonical binding before Scene construction.

## 4. LayoutPlacement handoff

Layout owns measurement and geometry. It produces immutable `LayoutPlacement` records:

- table column origins and widths;
- row/group/header bounds;
- mark tracks and mark bounds;
- axis intervals and label slots;
- decoration slots and annotation rails;
- relation obstacle geometry.

Scene owns semantic-to-primitive emission only. Scene may select a primitive's z-order and content from `PresentationContract`, but may not calculate column width, row height, track allocation, endpoint identity, or label-fit geometry.

## 5. Verification closure

`assert_presentation_contract` validates, before materialization:

1. every enabled contract semantic has a registry entry;
2. every required registry binding is present in the resolved theme;
3. every required placement exists and is non-overlapping where applicable;
4. emitted Scene primitives cover each enabled registry purpose;
5. each example manifest selects its declared context and public materializer output reproduces byte-for-byte.

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

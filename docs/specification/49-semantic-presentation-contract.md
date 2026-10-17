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

The registry owns canonical primitive semantics. Its entries declare `semantic_id`, primitive kind, Scene purpose, canonical theme binding, whether a binding is required, and materializer evidence requirement.

| Semantic id | Primitive | Scene purpose | Canonical theme binding |
| --- | --- | --- | --- |
| `planned` | Rect/Symbol | `planned` | `planned` |
| `actual` | Rect/Symbol | `actual` | `actual` |
| `asOf` | Path/Text | `as-of`, `as-of-label` | `asOf` |
| `deadlineMark` | Path | `deadline-mark` | `deadline-mark` (contrast class `mark`; the role is required when a View shows deadlines) |
| `deadlineMarkOutline` | Rect | `deadline-mark-outline` | `background` (completed opaque ground under the deadline stroke, not independently contrast-classified; Spec07 outlineWidth) |
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

## Issue419 design draft — resource vocabulary and declarative Style

**Proposed, not implemented or normative.** Reviewer approval is required before
code. Existing sections and Spec07/60 remain authoritative until the migration
below is accepted. The [design work record](../planning/active/issue-419-semantic-resource-work-record-2026-10-17.md)
contains the current117-binding inventory, architecture review and delivery slices.

### Resource boundary and authors' extension point

Separate the host's meaning catalogue from a design's treatment rules; do not
make Theme a semantic selector or turn Project profiles into a style language.

| Proposed resource | Contents and authority |
| --- | --- |
| `chrona/semantic-vocabulary/v0.1`, kind `semantic-vocabulary` | Schema-validated replacement for the Python binding table: semantic ID, primitive family, purpose, Scene role, Theme role, contrast class, and state-family classification. Shipped with the product; it declares host-produced meanings, not executable geometry. |
| `chrona/style/v0.2`, kind `style` | One rule mechanism over View-projected facts. An authored rule produces either a Theme-role reference or a colour-scale encoding. A new named distinction is a new rule, not a new host factory or purpose. This extends the historical Style design rather than introducing a third selector engine. |

Both use the shared presentation-resource envelope and exact pinned resource
references (Spec13/56). The vocabulary schema references existing common shape
and enum definitions, not copied patterns. Duplicate IDs, unsupported versions,
identity mismatch and missing referenced bytes fail closure; no directory scan,
network acquisition, ambient host default or package resolver is introduced.
The bundled vocabulary is explicit in a resolved render closure/provenance even
when a draft selects its wheel-owned default. Persistent Context/preset resource
members pin Style and vocabulary using existing identity rules.

Vocabulary IDs, purposes, primitive admission and contrast obligations are
host-owned. A design may add arbitrarily many rules over the admitted facts and
Theme roles, but cannot invent schedule facts, Scene kinds, purposes, adapter
capabilities or weaker contrast classes. Theme custom role names are permitted
only with a declared existing primitive family and typed Theme members;
selected roles must satisfy the original semantic's kind and contrast contract.
This is a visual distinction, not registration of a new domain meaning.

### Closed rule and encoding shape

The following is **proposed syntax**, not a currently accepted YAML example.
`fieldRole` resolves via Project bindings; explicit `field` uses the same tagged
field-reference path already used by colour encoding.

```yaml
# chrona-contract: historical
version: chrona/style/v0.2
kind: style
id: review-treatment
body:
  rules:
    - id: behind-cell
      when:
        purpose: table-cell
        columnSource: finishDelta
        comparisonCategory: behind
      then: {role: variance-behind}
    - id: payload-risk
      when:
        purpose: planned
        fields: [{source: {fieldRole: responsible}, equals: payload}]
      then:
        encode:
          channel: fill
          source: {field: risk}
          scale: risk
          domain: [low, high]
          legend: {title: 'Risk — payload team'}
```

`when` is intersection only. Initial closed selector keys are `semantic`,
`purpose`, `facet`, `sourceType`, `relationKind`, `comparisonCategory`,
`columnSource`, `roles` (all specified role facts), and `fields` (typed scalar
equality tests). Their value vocabularies come from the versioned catalogue or
existing projected fact contracts. No dotted-path evaluation, ordering of
numbers, regular expressions, title matching, expressions, coordinates, wall
clock, arbitrary negation, side effects or host callbacks are admitted.
An absent optional projected value does not match; an unknown selector,
undeclared field/role, wrong scalar type or unsupported target is a pointed
closure error, not a silent non-match. Missing source values on a matching
encoding retain Spec60's explicit scale-value refusal.

`roles` reads only the original View Projection's declared role facts (for
example missing-actual, variance category and scheduling-derived critical),
using catalogue-listed permitted values. It does not inspect a Theme name or
the result of this or another Style rule. This and `purpose`, `semantic`,
`columnSource` and typed `fields` intentionally extend Spec07's historical
four-key selector vocabulary; no arbitrary projected attribute becomes public.

Each rule has a unique stable ID and exactly one `then.role` or `then.encode`.
The first encoding channel is `fill`; admitted targets are the catalogue's
fillable existing semantic families, including planned/actual/snapshot member
marks and table cells. Unsupported combinations such as a fill-only encoding
on a stroke-only relation refuse closure. New channels need a separately
reviewed channel contract, not arbitrary Theme property names.
Spec60's total domain, firstAppearance order, palette folding, separability and
Theme scale→Scheme slot mapping are reused, not reimplemented in Style.
This successor intentionally transfers the authored encoding source/domain/
target declaration from View to Style; View still owns source availability,
selection and projected facts. The implementation must amend Spec06/60's
ownership clauses, not merely their single-encoding limit. Existing View
colorEncoding lowers into the same typed intent until the atomic migration
retires that syntax; Theme retains only the domain-value→Scheme-slot mapping.

Rules evaluate against original View facts, never roles produced by another
rule. Source order is evidence order, not last-wins precedence. Identical
assignments coalesce with all rule IDs retained. Two different role assignments
to one occurrence, or two encodings of its same channel, are errors naming both
rules and the occurrence. An explicit role and an encoding may coexist: role
first supplies typed base paint; the encoding replaces only its declared
channel. Roles/encodings targeting different channels or occurrences do not
conflict. Existing base semantic assignment applies when no rule matches;
there is no implicit catch-all or more-specific-wins rule.

### Projection, Style, Theme and Layout handoff

View owns selected occurrences and their immutable scheduling/comparison facts,
including stable object/relation/column identity and typed field access. Style
evaluates predicates and produces immutable occurrence-keyed role/encoding
intent plus matched rule IDs. Theme/Scheme resolution completes concrete paint
and typed typography/mark attributes before Layout uses them; Layout measures
and places using those attributes. Scene receives completed geometry and paint
relations. Neither Layout nor Scene interprets raw fields or authored rules.
Style does not create/drop occurrences, change dates, route relations, bypass
label-fit rules or supply coordinates. Text and stroke changes must enter Layout
before fit/routing; no adapter-time recolouring of already accepted geometry.

Issue344 plugs into this same field accessor: Project/profile schema validates
the declared namespaced field ID, scalar type and allowed values; View projects
that field on the appropriate source occurrence; Style references it with
`source: {field: ...}`. `fieldRole` is a Project-owned alias to that accessor,
not a second evaluator. Until typed-field support is implemented, only fields
admitted by the live Project contract may be used; the draft does not pretend
issue344 is implemented. Multi-source comparison uses the selected occurrence's
source identity explicitly, never an accidental primary-project lookup for a
Snapshot value. A field's absence is distinct from null and an invalid value.

### Scoped legends, diagnostics and complete coverage

Derived scale entries come from values actually painted after rule matching and
conflict resolution, in domain order. Identity includes Style/rule/scale/scope
and value; two differently scoped scales do not merge merely because labels
coincide. A non-global rule needs a declared non-empty legend title; Layout
renders that title with its swatches or applies the existing visible overflow
policy. An unqualified global legend may not describe a scoped encoding.
Global means `when` specifies only target `purpose` and/or `semantic`, with
no fact-dependent selectors. Every additional selector makes the encoding
scoped, even if every current occurrence happens to match. Scope identity is
the canonical normalized `when` JSON value (sorted keys, normalized set operands)
within the pinned Style/rule identity; it never depends on current match count
or human title text. That same selector is available for inspection beside the
authored legend title. A scoped legend also renders a qualifier derived from
the canonical selector's fact clauses (field/role/category names and literal
values), not only an author-chosen title: for example `responsible = payload`.
The title cannot hide or replace that qualifier. If its scope cannot be rendered
within the existing legend contract, refuse the scoped encoding rather than
emit an unqualified key. Swatches use completed paint, including the same palette-folded Other entry;
rules with no realized matches create no misleading entries. Existing semantic
legend keys remain separate and do not enumerate an encoding's domain.

New failure families must distinguish invalid vocabulary/rule declarations,
unknown facts, rule conflicts, incompatible role/target and unqualified legend
scope, carrying resource pointer, rule IDs and occurrence/subject identity.
Exact diagnostic spellings and shared definitions are finalized with the schema
slice; failures occur before usable Scene output. Existing scale errors remain
Spec60 errors. Successful Scene/CLI provenance reports matched rules without
turning intentional non-matches into warnings.

Coverage population is the union of resource-declared and actually drawn
purposes, not a curated family list. For each purpose report realized roles,
slides, declared state cardinality (or explicit unknown), realized state/role
pairs and an intentional-equivalence reason or gap. Count source model states
and role outcomes separately: roles alone do not prove state realization.
Every vocabulary purpose requires a classification; a new unclassified purpose
fails the check even if absent from the corpus. Existing three RealizationFamily
entries migrate to classifications, not population filters. The single-role
fraction and all unpainted/gap purposes appear in the committed checked report;
never copy the stale31-of-40 measurement. Public materializers and actual output
remain the evidence for realized values, not just a resource declaration.
The fraction's denominator is distinct purposes actually drawn in the committed
Scene corpus; its numerator is those with exactly one distinct realized visual
role across that corpus. Registered-but-unpainted purposes are separate rows,
not zero-role entries smuggled into that denominator. Model classifications
and rule-state coverage are additional columns, not substitutes for this count.

### RC promises, migration and non-goals

RC public surface: versioned envelope/ref identity, vocabulary semantic IDs,
purposes/kind admission, selector keys/value contracts, rule IDs and conflict
behavior, role/encoding shape, typed field reference, scoped legend meaning and
diagnostic identity. Internal: Python classes/functions, factory grouping,
cache representation, inventory row order and physical resource packaging.
The same public semantics must not depend on those internals. Exact draft names
above become promises only after reviewer/schema acceptance, not by publishing
this proposal.

Migration first externalizes the exact117 current bindings with equivalence
tests; no dual Python/resource authority. Then publish Style's schema and one
typed evaluator, lower existing View colorEncoding to that same intent, and
migrate builtin rules/resources and all affected Contexts/presets atomically.
If removing the old singleton syntax is necessary, use Spec56's incompatible
version successor and explicit migration rather than retain a parallel runtime.
Until that atomic slice, legacy input has only its existing behavior. Existing
Spec07 ordered addRoles and Spec60 single-encoding restrictions are superseded
only for the accepted successor, not silently reinterpreted.
Spec62/59 must be amended together: packages may carry supported declarative
Style resources, but still cannot register host facts or arbitrary geometry.
No package acquisition, continuous scale, expression engine, custom scheduler,
automatic field inference or renderer plugin belongs to this work.

### Prior-art lessons (not imported authority)

[Vega-Lite conditions](https://vega.github.io/vega-lite/docs/condition.html)
combine conditional selection with field/value encodings; Chrona reuses the
separation, not its expression surface. Its [legend contract](https://vega.github.io/vega-lite/docs/legend.html)
ties guides to scales; Chrona additionally requires honest predicate scope.
[DTCG format](https://www.designtokens.org/tr/2025.10/format/) provides typed
tokens, references and organizational groups; the lesson is explicit types and
reference errors, not inferring meaning from a folder name. It is not a rule
selection language and does not justify mixing Theme values with semantic facts.

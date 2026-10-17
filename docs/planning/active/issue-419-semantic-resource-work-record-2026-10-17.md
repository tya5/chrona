# Issue419 — semantic mapping resource

Status: design amendment applied per reviewer direction; implementation planning
may proceed from this record. Baseline: published main
`aabc5e894af50555892c0007e48efb24c268f2f3`.
[Owner scope](https://github.com/tya5/chrona/issues/419#issuecomment-6234067417):
design record only, after issue1657 (implementation now published in PR1662).

## Published baseline and open questions

- `semantic_registry.py` has117 actual `_binding` declarations, not123; verify
  the complete inventory and field consumers are recorded below.
  The issue's older claim that primitive kind and Theme role are unread is not
  current: Scene kind checks and Layout/Theme resolution consume them.
- Spec49 owns the closed semantic→Theme→placement→Scene contract. Spec06/60
  expose one planned-mark colour encoding. Project `fields` and field roles
  already reach projection; issue344's typed declaration is future work.
- Issue419's selected proposal is recorded here only; Spec49 remains unchanged
  until a normative change is implemented. Keep the existing View
  `colorEncoding` input accepted and lower it into the same typed intent used
  by Style. This work does not retire that syntax or require incompatible
  Context/preset migration.

## Literal acceptance (parent remains open during design-only scope)

1. The semantic vocabulary is a versioned resource with a schema.
2. A design set can introduce a visual distinction the product did not anticipate, without a code change.
3. The presentation coverage report derives distinctions from resources rather than from source.
4. No field in the registry is unread.
5. The report lists every purpose drawn in the corpus with its realized role count, generated from committed Scenes.
6. Adding a purpose to the semantic registry without a classification fails the check.
7. The 31-of-40 figure, or its successor, is visible in a committed, checked document.

Rows5–7 are the consolidated issue433 acceptance, not optional follow-ups.
The current deliverable specifies how to achieve these; it does not mark them
implemented or close the parent.

## Design plan and publication boundary

1. Inventory all current bindings, grouped by mechanism; trace meaning, role,
   paint and every field consumer. Separate stale measurements from current facts.
2. Define the versioned mapping resource/schema shape, YAML-addable
   distinctions and closed predicate vocabulary. Preserve existing View
   `colorEncoding` as an accepted input to the same typed intent.
3. Specify the single typed-field connection for issue344, RC public/internal
   contracts, conflict and missing-fact behavior, provenance and scoped legends.
4. Compare only needed lessons from official Vega-Lite encoding/conditions and
   design-token specifications; review whole-architecture ownership against
   Spec04/06/07/08/33/49/56/60/62 and adjacent designs.
5. Keep this work record as the proposal; update normative specifications only
   alongside the implementation slice that changes their contract. No schema,
   runtime, examples or generated changes in this design amendment.
6. Post one current Status linking this record. Implementation may proceed
   within the reviewed boundaries below; deferred choices remain explicit.

Evidence: complete117-entry inventory; synthetic YAML use cases for role and
scoped encoding outcomes; literal acceptance→planned test/report mapping;
architecture consistency and migration review. Docs/literal checks apply to
this publication; future implementation uses focused tests and official
public-output/full release CI rather than an unneeded local full suite.

## Architecture review and proposed implementation sequence

The proposal preserves Spec07's Style/Theme split and Spec49's
completed-placement boundary; it does not place predicates in Theme or
geometry in Style/Scene. Existing View `colorEncoding` remains valid and lowers
to the same typed intent; no incompatible syntax or atomic resource migration
is required. Spec04 dates and observed facts remain unchanged. Spec56 controls
resource identity and shared schema vocabulary. Issue344's typed Project field
uses the same source accessor; no profile-specific backdoor. Coverage433 is
derived from vocabulary plus actual Scenes and does not infer model cardinality
from role counts.

These are the reviewed implementation slices. V1 may begin after this amended
record is published; subsequent slices follow the stated dependency order:

| Slice | Owners / changes | Acceptance evidence and publication |
| --- | --- | --- |
| V1 | schemas/resource registration, semantic registry loader, wheel resource, Spec49/56 | All117 binding records equal old values; every field has a consumer; unknown/missing/duplicate/version/identity negatives; full materializer counts. Publish resource replacement without two authorities. Rows1/4. |
| S1 | View facts, Style evaluator/contracts, Theme-role compatibility, Spec06/07/60 | Neutral unseen field combination, role and encoding outcomes, conflicts/missing/type errors, repeated/source-specific occurrences; geometry uses resolved typography/strokes. Rows2/3. |
| S2 | closure, Style references, shipped resource support and legend composition | Same typed intent for Style and existing View `colorEncoding`; exact pins/copy/wheel closure; scoped swatches retain canonical selector in Scene/provenance. A scoped legend requires its title. The derived scope qualifier is opt-in, not forced; an unrenderable optional qualifier does not refuse otherwise valid encoding. No atomic migration or second evaluator. Rows2/3. |
| C1 | coverage/classification resources, tools, checked reports | Derive every registered/drawn purpose; state/role cardinalities distinct, unclassified purpose fails, intentional equivalences and current single-role fraction visible. Rows3/5/6/7. |

Each code publication needs focused neutral tests, official batched SVG/Scene
counts and design-conformance review, followed by CI's full release gate.
Final schema spellings and exact owned files are finalized in the implementation
plan; no draft numeric budgets or project-specific predicates become acceptance
requirements.

Reviewer confirmed this amendment in
[comment 6234922800](https://github.com/tya5/chrona/issues/419#issuecomment-6234922800)
and stated no additional review is needed if applied as written in
[comment 6234966527](https://github.com/tya5/chrona/issues/419#issuecomment-6234966527).
The reviewed inventory verification remains:117 unique rows exactly match the
117 AST bindings. This amendment changes documentation only; no
product/schema/examples/generated changes.

## Selected resource and Style contract

The host vocabulary (`chrona/semantic-vocabulary/v0.1`, kind
`semantic-vocabulary`) and authored Style (`chrona/style/v0.2`, kind `style`)
are separate resources using the shared envelope and exact pinned references.
The bundled
vocabulary replaces the Python binding table and declares semantic ID,
primitive family, purpose, Scene role, Theme role, contrast class and state
classification. It declares host-produced meanings, not geometry. Style rules
produce either a Theme-role reference or a color-scale encoding over
View-projected facts. A design may add rules over admitted facts and Theme roles,
but cannot invent schedule facts, Scene kinds, purposes, adapter capabilities,
or weaker contrast requirements. Custom Theme role names remain constrained by
primitive-family and contrast compatibility.

Resource identity, duplicate IDs, unsupported versions, missing referenced
bytes and identity mismatches fail closure. The vocabulary is explicit in
resolved closure/provenance, including when the wheel-owned default applies.
Context/preset references use existing pinning rules; they need not all migrate
atomically. Package support may carry supported declarative Style resources,
but packages cannot register host meanings or arbitrary geometry.

The illustrative YAML shape is:

```yaml
version: chrona/style/v0.2
kind: style
id: review-treatment
body:
  rules:
    - id: behind-cell
      when: {purpose: table-cell, columnSource: finishDelta, comparisonCategory: behind}
      then: {role: variance-behind}
    - id: payload-risk
      when:
        fields: [{source: {fieldRole: responsible}, equals: payload}]
      then:
        encode:
          channel: fill
          source: {field: risk}
          scale: risk
          domain: [low, high]
          legend: {title: 'Risk — payload team'}
```

This is a design example, not an accepted schema instance. Initial selector
keys are exactly `semantic`, `purpose`, `comparisonCategory`, `columnSource`,
`roles`, and `fields`, with these initial use cases and focused test subjects:

| Selector | Existing meaning or author use case |
| --- | --- |
| `semantic` | Target `forecast` separately from `planned` while retaining their existing shared Theme role. |
| `purpose` | Apply a treatment to planned marks across admitted span/point semantics. |
| `comparisonCategory` | Treat behind/on-track/ahead table occurrences as the current variance bindings do. |
| `columnSource` | Limit the variance treatment to `finishDelta` cells, as the example above does. |
| `roles` | Select the original scheduling-derived critical fact without reading a Theme name. |
| `fields` | Scope a risk encoding to the responsible payload team through the existing field-role alias. |

Defer `facet`, `sourceType`, and `relationKind` until named use cases are
approved. Predicates are intersection-only. `roles` reads only original View
Projection facts, never a Theme name or another rule's output. `fields` use the
existing typed source accessor. Missing optional facts do not match; unknown
selectors, undeclared fields/roles, wrong scalar types and incompatible targets
are pointed closure errors. No expression language, path traversal, arbitrary
negation, callbacks, coordinates, time, or numeric ordering is introduced.

Each rule has a unique ID and exactly one role or encoding outcome. The first
encoding channel is `fill` only. Its targets are admitted fillable semantic
families (planned/actual/snapshot member marks and table cells); a stroke-only
relation is not a fill target. Another channel requires its own reviewed
contract. Existing
Spec60 domain ordering, palette folding, separability and Theme scale-to-Scheme
mapping are reused. Existing View `colorEncoding` stays accepted and lowers to
the same typed intent as Style; there is no second evaluator and no retirement
or incompatible migration of the existing syntax. A matching encoding with a
missing source value retains Spec60's explicit refusal. Role and encoding may
coexist when they target distinct paint channels; conflicting assignments to
the same occurrence/channel fail with both rule IDs and occurrence identity.
Identical assignments coalesce with all matched rule IDs retained. Different
role assignments or different encodings of the same channel fail; input order
does not select a winner. No match retains existing semantic paint; there is no implicit catch-all or
specificity/last-wins precedence.

View owns occurrence selection, stable object/relation/column identity and
immutable facts. Style evaluates those facts into occurrence-keyed role/encoding
intent and matched-rule IDs. Theme/Scheme completes paint and typed typography/
mark attributes before Layout measurement and placement. Scene emits completed
geometry and paint relations; adapters do not interpret raw fields or authored
rules. Text/stroke changes therefore enter Layout before fit/routing.
Issue344's typed Project fields use this same field accessor: schema validates
namespaced ID/type/allowed values, View projects the field on its source
occurrence, and Style refers to it through `source: {field: ...}`. Do not add a
profile-specific lookup path. `fieldRole` remains a Project-owned alias into
that accessor, not a second evaluator. Until that field support exists, only fields
admitted by the live Project contract are usable. Multi-source comparisons
retain source identity; absence is distinct from null or invalid value.

## Scoped legends, diagnostics and coverage

Derived scale entries come from values actually painted after rule matching and
conflict resolution, in domain order. Identity includes Style/rule/scale/scope
and value. A non-global rule requires an authored non-empty legend title; the
canonical normalized selector is available beside swatches in Scene and
provenance. A visible qualifier derived from that selector is an opt-in legend
member, not mandatory output. If the optional qualifier cannot be rendered,
that alone does not refuse the encoding. A scoped key must not be described as
global. Scope identity is the canonical normalized `when` JSON under pinned
Style/rule identity, not title text or current match count. Rules with no
realized matches produce no misleading scale entry. Global means the rule uses
only `purpose` and/or `semantic`; any additional fact selector is scoped even
when all current occurrences match. Swatches use the completed paint, including
palette-folded Other. Semantic legend keys remain
separate.

Failure diagnostics distinguish invalid vocabulary/rules, unknown facts,
conflicts, incompatible role/target and missing required legend title, and carry
resource pointer, rule IDs and subject identity. Existing scale errors remain
Spec60 errors. Successful provenance reports matched rules without warning on
intentional non-matches.

Coverage is derived from vocabulary plus committed Scene outputs, not a curated
source list. Every registered purpose requires a classification, even if not
currently drawn. Report drawn-purpose realized role counts and slides, model
state cardinality separately, realized state/role pairs, intentional
equivalences or gaps, and unpainted purposes. The Issue433 numerator is the
number of distinct drawn purposes with exactly one realized visual role; its
denominator is all distinct purposes actually drawn. Registered-but-unpainted
purposes remain separate rows, not zero-role denominator entries. The current
117-entry inventory and 31/40 historical figure are baseline evidence only;
the generated checked report supplies the successor measurement.

## RC, ownership and release conditions

RC promises versioned resource envelope/identity, vocabulary semantic IDs,
purposes, Theme-role names and existing `colorEncoding`. Style v0.2 is an RC
promise only if V1, S1 and S2 land before the RC trial; otherwise it remains
experimental. V1 must precede RC. Dev A owns V1/S1/S2. Dev B begins C1 after V1
and owns Issue344 Level 1 in the meantime, using the same accessor described
above. Python types, factory grouping, cache representation, inventory order
and physical packaging are internal. Focused neutral tests, public materializer
evidence and the release CI gate are required at each implementation boundary.

## Prior-art lessons

[Vega-Lite conditions](https://vega.github.io/vega-lite/docs/condition.html)
separate predicates from field/value encodings; retain that separation, not an
expression language. Its [legends](https://vega.github.io/vega-lite/docs/legend.html)
follow resolved scales; Chrona additionally records predicate scope and requires
an authored title for a scoped key.
[DTCG format](https://www.designtokens.org/tr/2025.10/format/) contributes typed
values and explicit references/errors, not semantic inference from folders or a
reason to mix Theme values with View facts.

## Current registry inventory (117 entries)

This inventory groups entries by the mechanism families in
`presentation/model/semantic_registry.py`, not by primitive kind. Counts by
kind are 9 marks, 13 lines, 39 decorations, 54 labels, and 2 icons. The
contrast totals are 39 unclassified, 38 `GROUND_TEXT`, 22 `DECORATION`, 9
`MARK`, and 9 `STATE_TEXT`. `—` means no contrast class is declared.

The fields are consumed as follows: `semantic_id` is the closed lookup key for
`semantic_binding()` and family helpers; `primitive_kind` constrains Scene
primitive compatibility and lane-purpose validation; `purpose` is carried
into Scene/serialization and used in validation and contrast resolution;
`scene_role` is the completed paint role used by Scene construction and
contrast classification; `theme_role` selects the Theme paint/typography
role in Layout/Scene resolution; `contrast` is optional policy input used by
Scene validation and `scene/contrast_policy.py`. The principal consumer is
`scene/v05_builder.py`; additional consumers include `scene/model.py`,
`scene/pattern_host.py`, `scene/contrast_policy.py`, Layout's lane/axis/legend/
background/label modules, and resource/Theme resolution. These are current
code facts, not a proposed resource contract.

Each row is `semantic | kind | purpose | Scene role | Theme role | contrast`.

### Comparison marks and icons

| Semantic | Kind | Purpose | Scene role | Theme role | Contrast |
|---|---|---|---|---|---|
| planned | mark | planned | planned | planned | MARK |
| forecast | mark | forecast | planned | planned | — |
| actual | mark | actual | actual | actual | MARK |
| snapshot | mark | snapshot | snapshot | snapshot | MARK |
| gate | mark | planned | gate | gate | MARK |
| missingActual | mark | missingActual | missing-actual | missing-actual | MARK |
| summaryBar | mark | summary-bar | summary-bar | summaryBar | MARK |
| progressFill | mark | progress-fill | progress-fill | progressFill | MARK |
| iconMark | icon | icon-mark | icon-mark | icon-mark | — |
| labelVisual | icon | label-visual | text | text | — |

### Time, deadline, calendar, period, and canvas

| Semantic | Kind | Purpose | Scene role | Theme role | Contrast |
|---|---|---|---|---|---|
| asOf | line | as-of | as-of | asOf | — |
| asOfLabel | label | as-of-label | text | text | GROUND_TEXT |
| asOfCone | decoration | as-of-cone | as-of-cone | as-of-cone | — |
| deadlineMark | line | deadline-mark | deadline-mark | deadline-mark | MARK |
| deadlineMarkOutline | decoration | deadline-outline | deadline-mark-outline | background | — |
| deadlineCaption | label | deadline-caption | text | text | GROUND_TEXT |
| asOfLabelChip | decoration | label-chip | as-of-label-chip | as-of-label-chip | — |
| calendarClosed | decoration | calendar-closed | calendar-closed | calendarClosed | DECORATION |
| calendarException | decoration | calendar-exception | calendar-exception | calendarException | DECORATION |
| periodBand | decoration | period-band | period-band | period-band | DECORATION |
| periodLabel | label | period-label | period-label | period-label | STATE_TEXT |
| periodLabelChip | decoration | label-chip | period-label-chip | period-label-chip | — |
| canvasTexture | decoration | canvas-texture | canvas-texture | canvas-texture | — |
| canvasOverlay | decoration | canvas-overlay | canvas-overlay | canvas-overlay | — |
| canvasOverlayGradient | decoration | canvas-overlay-gradient | canvas-overlay-gradient | canvas-overlay-gradient | — |
| regionFrame | decoration | region-frame | region-frame | region-frame | — |
| frameGlyph | decoration | frame-glyph | frame-glyph | frame-glyph | — |

### Axis bands, labels, and rules

| Semantic | Kind | Purpose | Scene role | Theme role | Contrast |
|---|---|---|---|---|---|
| axisBand | label | axis-band | axis-band | axis | GROUND_TEXT |
| axisBandDecoration | decoration | axis-band | axis-band-decoration | axis-band-decoration | DECORATION |
| axisBandDecoration2 | decoration | axis-band | axis-band-decoration2 | axis-band-decoration2 | DECORATION |
| axisLabel | label | axis-label | text | axis | GROUND_TEXT |
| axisLabel2 | label | axis-label | axis-label2 | axis2 | GROUND_TEXT |
| axisLabel3 | label | axis-label | axis-label3 | axis3 | GROUND_TEXT |
| axisGrid | line | axis-grid | axis-major | axis-major | — |
| axisGridMinor | line | axis-grid | axis-minor | axis-minor | — |
| axisRule | line | axis-rule | axis-rule | axis-rule | — |
| axisCellSeparator | line | axis-cell-separator | axis-cell-separator | axis-cell-separator | — |

### Grouping, rows, observations, and table

| Semantic | Kind | Purpose | Scene role | Theme role | Contrast |
|---|---|---|---|---|---|
| groupBand | decoration | group-decoration | group-band | group-band | DECORATION |
| rowBand | decoration | row-decoration | row-band | row-band | DECORATION |
| rowRule | decoration | row-rule | row-rule | row-rule | DECORATION |
| tableColumnRule | decoration | table-column-rule | tableColumnRule | tableColumnRule | DECORATION |
| groupHeaderBand | decoration | group-header-band | group-header-band | group-header-band | DECORATION |
| groupHeaderStrip | decoration | group-header-strip | group-header-strip | group-header-strip | DECORATION |
| groupTab | decoration | group-tab | group-tab | group-tab | DECORATION |
| groupHeader | decoration | group-header | group-header | groupHeader | GROUND_TEXT |
| groupDetail | label | group-detail | text | text | GROUND_TEXT |
| observationSource | label | observation-source | text | text | GROUND_TEXT |
| observationColumnLabel | label | observation-column-label | text | text | GROUND_TEXT |
| observationCell | label | observation-cell | text | text | GROUND_TEXT |
| observationAttentionCell | label | observation-cell | variance-ahead | variance-ahead | — |
| observationCriticalCell | label | observation-cell | variance-behind | variance-behind | — |
| titleText | label | title-text | heading | heading | GROUND_TEXT |
| kickerText | label | kicker-text | kicker | kicker | GROUND_TEXT |
| subtitleText | label | subtitle-text | subtitle | subtitle | GROUND_TEXT |
| slotHeading | label | slot-heading | slot-heading | slot-heading | GROUND_TEXT |
| tableColumnLabel | label | table-column-label | text | text | GROUND_TEXT |
| tableCell | label | table-cell | text | text | GROUND_TEXT |
| tableVarianceAhead | label | table-cell | variance-ahead | variance-ahead | STATE_TEXT |
| tableVarianceOnTrack | label | table-cell | variance-on-track | variance-on-track | STATE_TEXT |
| tableVarianceBehind | label | table-cell | variance-behind | variance-behind | STATE_TEXT |
| missingActualCell | label | table-cell | missing-actual-cell | missing-actual-cell | STATE_TEXT |

### Plot member labels and finish deltas

| Semantic | Kind | Purpose | Scene role | Theme role | Contrast |
|---|---|---|---|---|---|
| memberLabel | label | member-label | text | text | GROUND_TEXT |
| memberLabelInsidePlanned | label | member-label | member-label-inside-planned | member-label-inside-planned | GROUND_TEXT |
| memberLabelInsideActual | label | member-label | member-label-inside-actual | member-label-inside-actual | GROUND_TEXT |
| memberLabelInsideSnapshot | label | member-label | member-label-inside-snapshot | member-label-inside-snapshot | GROUND_TEXT |
| memberLabelInsideScenario | label | member-label | member-label-inside-scenario | member-label-inside-scenario | GROUND_TEXT |
| memberLabelChip | decoration | label-chip | member-label-chip | member-label-chip | — |
| finishDelta | label | finish-delta | variance-on-track | variance-on-track | — |
| varianceAhead | label | finish-delta | variance-ahead | variance-ahead | — |
| varianceBehind | label | finish-delta | variance-behind | variance-behind | — |
| forecastFinishDelta | label | forecast-finish-delta | variance-on-track | variance-on-track | — |
| forecastVarianceAhead | label | forecast-finish-delta | variance-ahead | variance-ahead | — |
| forecastVarianceBehind | label | forecast-finish-delta | variance-behind | variance-behind | — |
| finishDeltaChip | decoration | label-chip | finish-delta-chip | finish-delta-chip | — |
| milestoneDigestEntry | label | milestone-digest-entry | text | text | GROUND_TEXT |

### Relations and network

| Semantic | Kind | Purpose | Scene role | Theme role | Contrast |
|---|---|---|---|---|---|
| dependency | line | dependency | dependency | dependency | — |
| dependencyHalo | decoration | dependency-halo | dependency-halo | dependency-halo | DECORATION |
| dependency-critical | line | dependency | dependency-critical | dependency-critical | — |
| relationLabel | label | relation-label | text | annotation | GROUND_TEXT |
| networkNode | mark | network-node | network-node | network-node | MARK |
| networkLabel | label | title-text | text | text | GROUND_TEXT |
| networkEdge | line | network-edge | network-edge | network-edge | — |
| criticalEdge | line | critical-edge | critical-edge | critical-edge | — |

### Legend, notes, and annotations

| Semantic | Kind | Purpose | Scene role | Theme role | Contrast |
|---|---|---|---|---|---|
| legendEntry | decoration | legend-swatch | legend-swatch | legend-swatch | — |
| scaleLegendEntry | decoration | legend-swatch | planned | planned | — |
| legendLabel | label | legend-label | text | legend | GROUND_TEXT |
| projectNote | label | project-note | text | annotation | GROUND_TEXT |
| annotationListText | label | annotation-list-text | text | annotation | GROUND_TEXT |
| noteIndex | label | note-index | note-index | note-index | GROUND_TEXT |
| annotationCalloutBox | decoration | annotation-box | annotation-callout-box | annotation-callout-box | — |
| annotationCalloutText | label | annotation-text | annotation-callout-text | annotation-callout-text | GROUND_TEXT |
| annotationCalloutLeader | line | annotation-leader | annotation-callout-leader | annotation-callout-leader | — |
| annotationHighlightBox | decoration | annotation-box | annotation-highlight-box | annotation-highlight-box | — |
| annotationHighlightText | label | annotation-text | annotation-highlight-text | annotation-highlight-text | GROUND_TEXT |
| annotationNoteBox | decoration | annotation-box | annotation-note-box | annotation-note-box | DECORATION |
| annotationNoteText | label | annotation-text | annotation-note-text | annotation-note-text | STATE_TEXT |
| annotationNoteLeader | line | annotation-leader | annotation-note-leader | annotation-note-leader | — |
| annotationArrowBox | decoration | annotation-box | annotation-arrow-box | annotation-arrow-box | — |
| annotationArrowText | label | annotation-text | annotation-arrow-text | annotation-arrow-text | GROUND_TEXT |
| annotationArrowLeader | line | annotation-leader | annotation-arrow-leader | annotation-arrow-leader | — |
| annotationKindBar | decoration | annotation-kind-bar | annotation-kind-bar | annotation-kind-bar | DECORATION |
| annotationKindAccent | decoration | annotation-kind-accent | annotation-kind-accent | annotation-kind-accent | DECORATION |
| annotationKindStamp | decoration | annotation-kind-stamp | annotation-kind-stamp | annotation-kind-stamp | DECORATION |
| annotationArtwork | decoration | annotation-artwork | annotation-artwork | annotation-artwork | DECORATION |
| annotationBorderStart | decoration | annotation-border-start | annotation-border-start | annotation-border-start | DECORATION |
| annotationBorderEnd | decoration | annotation-border-end | annotation-border-end | annotation-border-end | DECORATION |
| annotationBorderTop | decoration | annotation-border-top | annotation-border-top | annotation-border-top | DECORATION |
| annotationBorderBottom | decoration | annotation-border-bottom | annotation-border-bottom | annotation-border-bottom | DECORATION |
| annotationKindLabel | label | annotation-kind-label | annotation-kind-label | annotation-kind-label | STATE_TEXT |
| annotationKindSecondary | label | annotation-kind-secondary | annotation-kind-secondary | annotation-kind-secondary | STATE_TEXT |
| annotationHeading | label | annotation-heading | annotation-heading | annotation-heading | STATE_TEXT |

### Summary panels

| Semantic | Kind | Purpose | Scene role | Theme role | Contrast |
|---|---|---|---|---|---|
| summaryHeader | label | summary-header | text | summary | GROUND_TEXT |
| summaryMetric | label | summary-metric | text | summary | GROUND_TEXT |
| summaryFigureValue | label | summary-figure-value | metric | metric | GROUND_TEXT |
| summaryFigureCaption | label | summary-figure-caption | subtitle | subtitle | GROUND_TEXT |
| summaryCaption | label | summary-caption | summary-caption | summary-caption | GROUND_TEXT |
| summaryUnit | label | summary-unit | summary-unit | summary-unit | GROUND_TEXT |

# Issue419 — semantic mapping resource

Status: selected design draft; no product implementation authorized before reviewer
review. Baseline: published main `aabc5e894af50555892c0007e48efb24c268f2f3`.
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
- The [Spec49 design draft](../../specification/49-semantic-presentation-contract.md#issue419-design-draft--resource-vocabulary-and-declarative-style)
  selects separate host vocabulary and authored Style resources, closed facts,
  role-or-encoding outcomes, explicit conflicts, scoped legends and derived
  coverage. It is a proposal, not a new live contract.

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
2. Draft one versioned mapping resource/schema shape, YAML-addable distinctions
   and a closed predicate vocabulary combined with existing colour encoding.
3. Specify the single typed-field connection for issue344, RC public/internal
   contracts, conflict and missing-fact behavior, provenance and scoped legends.
4. Compare only needed lessons from official Vega-Lite encoding/conditions and
   design-token specifications; review whole-architecture ownership against
   Spec04/06/07/08/33/49/56/60/62 and adjacent designs.
5. Publish the selected design in a clearly non-normative Spec49 draft section;
   record migration and independently reviewable implementation slices here.
   No schema, runtime, examples or generated changes in this design publication.
6. Post one current Status linking the record and draft. Await reviewer before
   product implementation; unresolved design choices stay explicit.

Evidence: complete117-entry inventory; synthetic YAML use cases for role and
scoped encoding outcomes; literal acceptance→planned test/report mapping;
architecture consistency and migration review. Docs/literal checks apply to
this publication; future implementation uses focused tests and official
public-output/full release CI rather than an unneeded local full suite.

## Architecture review and proposed implementation sequence

The draft preserves Spec07's Style/Theme split and Spec49's completed-placement
boundary; it does not place predicates in Theme or geometry in Style/Scene.
Spec06/60's field/domain/scale split becomes one typed intent path rather than
a second encoding evaluator. Spec04 dates and observed facts remain unchanged.
Spec56 controls new kind registration, identity, shared schema vocabulary and
incompatible syntax migration. Spec59/62's package non-authority must be amended
only to admit supported Style members, not new host meanings. Issue344's future
typed Project fields use the same source accessor; no profile-specific backdoor.
Coverage433 is derived from vocabulary+actual Scenes and does not infer model
cardinality from role counts. Rule evaluation and scoped legend correctness
are release gates, not optional local styling polish.

These are proposed reviewable slices, **not authorization to implement**:

| Slice | Owners / changes | Acceptance evidence and publication |
| --- | --- | --- |
| V1 | schemas/resource registration, semantic registry loader, wheel resource, Spec49/56 | All117 binding records equal old values; every field has a consumer; unknown/missing/duplicate/version/identity negatives; full materializer counts. Publish resource replacement without two authorities. Rows1/4. |
| S1 | View facts, Style evaluator/contracts, Theme-role compatibility, Spec06/07/60 | Neutral unseen field combination, role and encoding outcomes, conflicts/missing/type errors, repeated/source-specific occurrences; geometry uses resolved typography/strokes. Rows2/3. |
| S2 | closure, Context/preset references, shipped resources and legend composition | One encoding IR, exact pins/copy/wheel closure, scope-labelled realized swatches, zero-match and conflicting scopes, all affected shipped resources migrate atomically. No partially materializable release or legacy second evaluator. Rows2/3. |
| C1 | coverage/classification resources, tools, checked reports | Derive every registered/drawn purpose; state/role cardinalities distinct, unclassified purpose fails, intentional equivalences and current single-role fraction visible. Rows3/5/6/7. |

Each code publication needs focused neutral tests, official batched SVG/Scene
counts and design-conformance review, followed by CI's full release gate.
Final schema spellings, exact owned files and migration version are finalized in
the implementation plan after reviewer approval; no draft numeric budgets or
project-specific predicates become acceptance requirements.

Reviewer decisions requested: approve the separate vocabulary/Style boundary,
closed initial selectors/channel, fail-on-conflict and scoped legend contract,
RC public surface, and the atomic migration order. If changed, update this
record and Spec49 draft before product code; Git preserves superseded text.

Independent design review tightened scope identity/title rules, the original
Projection owner of role predicates, the intentional View→Style encoding/domain
declaration migration, and the exact corpus single-role fraction. All are now
explicit in the draft. Verification:117 unique inventory rows exactly match
the117 AST bindings;13 docs tests, literal-review validation and all38
conformance checks pass. No product/schema/examples/generated changes.

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

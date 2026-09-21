# think-cell Gantt Research and Chrona Adoption Analysis

**Status:** Research / proposal  
**Date:** 2026-09-21  
**Scope:** think-cell Gantt capabilities that are relevant to Chrona presentation, layout, and interaction design.

## 1. Executive summary

think-cell and Chrona overlap in project-timeline presentation, but they optimize different boundaries.

think-cell is strongest as an interactive PowerPoint authoring experience. Its Gantt implementation reduces manual presentation work through adaptive calendar scales, automatic label placement, self-adjusting layout, calendar-aware timeline items, flexible status columns, and direct manipulation.

Chrona is designed around a different source-of-truth boundary: semantic Project data is evaluated through temporal and scheduling semantics and then projected through View, Style, Theme, Scene, and output adapters. Presentation state must not redefine scheduling or Project meaning.

The most valuable lesson for Chrona is therefore **not to copy think-cell's PowerPoint object model**. It is to bring think-cell's low-friction presentation behavior into Chrona's declarative and reproducible presentation pipeline.

The highest-value candidates are:

1. adaptive time-axis selection;
2. content-aware layout and automatic label placement;
3. a richer but bounded catalog of Gantt presentation marks;
4. data-driven semantic table columns;
5. direct manipulation translated into semantic Commands rather than Scene mutation.

The first two should be treated as one architectural theme: **adaptive presentation layout**. Users should declare presentation intent and constraints; Chrona should derive concrete geometry from content, font metrics, viewport, time window, and output capabilities.

## 2. Sources

Primary external sources reviewed:

- think-cell Gantt product overview: https://www.think-cell.com/en/product/gantt
- think-cell Gantt manual: https://www.think-cell.com/en/resources/manual/gantt
- think-cell chart product overview: https://www.think-cell.com/en/product/think-cell-charts
- think-cell automatic-layout manual: https://www.think-cell.com/en/resources/manual/automatic-layout
- think-cell style-file manual: https://www.think-cell.com/en/resources/manual/style-files

Chrona comparison is based on the repository's current specifications and implementation, especially the Project -> Temporal -> Scheduling -> View -> Style -> Theme -> Scene architecture and the current presentation/layout implementation.

## 3. Product-boundary comparison

| Concern | think-cell | Chrona |
|---|---|---|
| Primary environment | PowerPoint add-in | Structured project model plus render/automation surfaces |
| Authoritative planning model | Presentation/data-link oriented | Semantic Project and immutable evaluation inputs |
| Temporal/scheduling semantics | Gantt/calendar interaction oriented | Explicit Temporal and Scheduling models |
| Presentation editing | Strong direct manipulation | Declarative resources plus Command-oriented editing architecture |
| Multiple presentations | Multiple PowerPoint charts/slides | Multiple Views/Render Contexts over one Project |
| Appearance | Interactive formatting and style files | Style, Theme, presentation settings, layout/profile resources |
| Actual/baseline comparison | Can be represented in presentation data | Explicitly separated evaluation inputs and comparison semantics |
| Revision/reproducibility | Not the central product boundary | Revision Store, pinned resources, content identity |
| Automation | Excel linking and PowerPoint automation | CLI, typed Commands, AI proposals, adapters |
| Federation | Not a primary Gantt concept | Explicit independently owned subproject integration |

This difference is important when adopting features. A presentation convenience must not introduce a second scheduling model or renderer-owned semantic state.

## 4. Relevant think-cell capabilities

### 4.1 Adaptive calendar scales

think-cell supports calendar scales such as days, weeks, months, quarters, calendar years, and fiscal years. By default it can automatically add or remove calendar scales and separators according to the date range, chart size, and font size. Users can override this automatic behavior.

It also provides operations such as fitting the visible scale to the data, weekend presentation, configurable week starts, and flexible date formatting.

**Chrona relevance:** high.

Chrona already owns temporal meaning separately from presentation. Scale selection therefore belongs downstream of scheduling, in presentation-axis/layout evaluation. The semantic Date or DateTime values must remain unchanged.

### 4.2 Self-adjusting layout

think-cell emphasizes editing content rather than manually maintaining row heights and column widths. Gantt layout adapts when content is added or removed. General think-cell automatic layout also fits content and preserves dynamic alignments.

**Chrona relevance:** very high.

Chrona's layout system should increasingly accept intent and constraints rather than requiring authors to encode incidental geometry. Layout results can remain deterministic by including content metrics, font metrics, viewport, time window, layout/profile version, and target capabilities in the evaluation inputs.

### 4.3 Automatic label placement with manual override

think-cell automatically chooses timeline-item label positions based on layout, while allowing a user to pin a manual position and later restore automatic placement.

**Chrona relevance:** high.

This suggests a useful distinction between:

- automatic placement policy;
- declarative placement preference/constraint;
- explicit user override.

A manual override should remain presentation state and should not mutate Project semantics.

### 4.4 Gantt-specific timeline items

think-cell provides more than bars and milestones. Relevant presentation items include:

- bars;
- pentagons/chevrons (process arrows);
- milestones;
- brackets;
- shades;
- milestone lines;
- row separators and row shading.

**Chrona relevance:** high, but these should be presentation marks, not new Core temporal primitives.

A possible bounded Chrona vocabulary is:

```text
SpanMark
  bar
  chevron
  capsule
  phase-band

PointMark
  diamond
  circle
  flag

RangeDecoration
  bracket
  shade
  highlight

ReferenceDecoration
  milestone-line
  today-line
  deadline-line
```

A single TemporalSpan could therefore appear as a detailed bar in an engineering View, a chevron in an executive View, or a phase band in a roadmap View without changing the Project.

### 4.5 Flexible data-driven columns

think-cell supports activity, responsibility, and remark columns and can display data-driven indicators such as Harvey balls and checkboxes. Labels may span multiple rows.

**Chrona relevance:** high.

Chrona's table-timeline direction can generalize this into typed semantic columns:

```yaml
columns:
  - source: title
    mark: text
  - source: owner
    mark: badge
  - source: progress
    mark: progress
  - source: actualVariance
    mark: variance
  - source: risk
    mark: status
```

The key abstraction is **typed/derived value -> bounded presentation mark**, not a think-cell-specific indicator clone.

### 4.6 Calendar-linked anchors and direct manipulation

think-cell timeline items can be anchored to dates or other items. Moving an anchored item updates the related presentation geometry/dates. Excel-linked anchors can also update charts.

**Chrona relevance:** high for interaction, but it must be translated through Chrona's semantic authority boundary.

The desired Chrona interaction is:

```text
pointer gesture
  -> Scene hit-test
  -> semantic source identity
  -> gesture interpretation
  -> typed Command
  -> validation / scheduling
  -> View projection
  -> SceneDelta
```

The editor must not make the Scene or SVG authoritative.

### 4.7 Style customization

think-cell supports organization-specific Gantt appearance through style files, including default formatting and fiscal-calendar options.

**Chrona relevance:** moderate as a product lesson, but Chrona already has the stronger architectural separation of Style and Theme. The useful lesson is to make organization-level defaults easy to package and select without merging them into Project semantics.

## 5. Gap analysis against Chrona

| Candidate | Existing Chrona foundation | Main gap | Proposed owner |
|---|---|---|---|
| Adaptive time axis | Temporal model, presentation axis, layout/profile pipeline | Automatic scale hierarchy/density selection from available space | Presentation Axis + Layout |
| Content-aware sizing | Layout solver, presentation settings, font metrics | More intrinsic sizing and fewer author-specified geometry constants | Layout |
| Automatic label placement | Presentation labels/layout | General collision-aware candidate placement and stable override policy | Layout / Scene projection |
| Rich Gantt marks | Scene/presentation marks and SVG output | Consistent bounded mark catalog across profiles | Presentation / Scene |
| Semantic indicator columns | Table-timeline projection | General typed-value-to-mark column grammar | View + Presentation |
| Direct manipulation | Editor, gestures, Commands, SceneDelta concepts | Productized semantic gesture mapping and presentation override UX | Interactive adapter + Command |
| Fiscal/working calendar display | Calendar semantics and axis rendering | Presentation policies for hiding/shading/nonworking periods | View / Axis |
| Fit scale to data | View windows and layout | Explicit declarative auto-window policy with deterministic padding | View / Layout |

## 6. Recommended design direction

### 6.1 Priority 1 — Adaptive presentation layout

Treat the following as one coherent capability rather than isolated renderer fixes:

- adaptive axis hierarchy;
- content-aware row and column sizing;
- automatic label placement;
- collision avoidance;
- dependency routing;
- viewport-aware density.

Conceptually:

```text
Presentation intent
      +
View projection
      +
Content metrics
      +
Font metrics
      +
Viewport / target capability
      v
Constraint layout
      v
Reviewable Layout Manifest
      v
Scene
```

A user should prefer declarations such as:

```yaml
axis:
  mode: adaptive
  preferredLevels: [year, quarter, month, week, day]

rows:
  height: adaptive
  min: 22
  max: 48

labels:
  placement: automatic
  overflow: reflow
```

over fixed values such as month pixel widths and label offsets.

The output must remain deterministic for identical explicit inputs.

### 6.2 Priority 2 — Bounded presentation-mark catalog

Add expressive marks only where they are renderer-neutral and source-traceable. Marks should express presentation intent, not introduce new scheduling authority.

A mark must identify its semantic source, accessibility text, style role, and layout constraints.

### 6.3 Priority 3 — Semantic table-column marks

Extend table-timeline columns so typed Project fields, derived scheduling facts, Actual comparison facets, and review facts can map to compact visual marks.

Unknown or unavailable values must remain explicit rather than being rendered as favorable status.

### 6.4 Priority 4 — Semantic direct manipulation

Use think-cell as a UX benchmark for low-friction manipulation, but preserve Chrona's architecture. Dragging a scheduled object should create a proposed semantic change, not write coordinates.

Presentation-only adjustments such as label placement may use a presentation Command and View-local state.

## 7. What should not be copied

The following would weaken Chrona if adopted literally:

1. **Presentation geometry as project truth.** Scene/SVG/interactive coordinates must remain derived.
2. **Implicit relationship semantics from visual anchoring.** A visual attachment is not automatically a scheduling dependency.
3. **Hidden environment defaults.** Automatic layout may be adaptive, but every input needed for reproducibility must be explicit in the evaluation closure.
4. **A second Gantt-only scheduling model.** Gantt presentation must consume the existing Temporal/Scheduling result.
5. **Unbounded presentation scripting.** Expressiveness should remain declarative and deterministic; arbitrary renderer code does not belong in Project resources.

## 8. Proposed follow-up design work

Before implementation, perform a design pass against the current View, presentation-axis, layout-expression, Scene, and Command specifications.

Recommended outputs:

1. inventory current fixed presentation geometry and classify each value as semantic, presentation intent, derived metric, or accidental implementation constant;
2. define an adaptive-axis policy and deterministic selection algorithm;
3. define intrinsic-size inputs and the Layout Manifest additions needed for content-aware sizing;
4. define label-placement candidates, collision rules, override persistence, and diagnostics;
5. define the initial bounded presentation-mark catalog;
6. define typed table-column mark mapping;
7. review gesture-to-Command mappings for direct manipulation;
8. add acceptance fixtures demonstrating that the same Project can render at executive, detailed, and compact densities without changing semantic data.

## 9. Acceptance principles

Any adopted feature should preserve these Chrona properties:

- Project semantics remain independent of presentation.
- Temporal and Scheduling remain the sole authorities for planned placement.
- View chooses/selects presentation content without copying Project facts.
- Style maps semantic state to roles; Theme supplies concrete visual values.
- Layout derives geometry from explicit, reproducible inputs.
- Scene remains renderer-neutral and derived.
- Interactive edits cross the Command boundary.
- Automatic behavior is deterministic and diagnosable.
- Presentation extensions do not become hidden semantic extensions.

## 10. Overall assessment

think-cell demonstrates that a high-quality Gantt experience depends heavily on reducing manual presentation maintenance. Its strongest lesson for Chrona is not a particular milestone shape or PowerPoint interaction; it is that **layout should actively preserve readability as project content changes**.

Chrona can take that idea further because presentation is already separated from semantic truth. The architectural opportunity is to make the presentation pipeline more autonomous while remaining deterministic:

> Authors declare what they want to communicate; Chrona derives how to fit it into the requested presentation surface.

That direction strengthens rather than compromises the Project -> Temporal -> Scheduling -> View -> Style -> Theme -> Scene separation.

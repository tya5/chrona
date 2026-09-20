# Style and Theme

**Status:** Draft
**Depends on:** [06 View Model](06-view-model.md), [01 Concepts](01-concepts.md), [02 Domain Model](02-domain-model.md)
**Leads to:** `08 Scene and Rendering`

## 1. Purpose

This document defines how a Chrona view acquires a visual language without changing its meaning.

The **Style** layer maps the semantic objects and comparison facets emitted by the View Model to named visual roles. The **Theme** layer supplies concrete visual tokens for those roles. Together they make the same Project and View usable in a compact engineering review, a plan-versus-actual review, or a presentation-oriented timeline while preserving a small, reviewable semantic source.

Neither layer is a scheduling engine, a second project model, or an editable drawing canvas.

## 2. Design drivers

Chrona must offer more presentation freedom than text-only diagram grammars, but must not turn visual coordinates or opaque editor state into the source of truth. It must also remain narrower than a general project-management suite.

Therefore:

- Style is declarative and selects from semantic information already available to the View.
- Theme supplies reusable named tokens instead of scattering literal colours, fonts, and line widths through View definitions.
- A renderer consumes the resolved result; it does not infer planning semantics from pixels.
- Semantic dependencies and explanatory arrows must remain separately identifiable after styling.

## 3. Layer responsibilities

| Layer | Owns | Must not own |
|---|---|---|
| Project / Snapshot / Actual | Planning facts, baseline facts, independently observed actual facts | Visual appearance |
| View | Selected objects, grouping, order, comparison context, logical annotation placement | Literal visual tokens or scene coordinates |
| Style | Semantic selector to visual-role resolution | Colours, fonts, geometry, or scheduling rules |
| Theme | Visual-role token values and token inheritance | Semantic conditions or object selection |
| Scene | Renderer-neutral graphics primitives and concrete placement | Semantic selection or theme policy |

This boundary is normative. Moving a concern upward is allowed only when it does not introduce presentation information into Project semantics; moving it downward must not require a renderer to reconstruct lost meaning.

## 4. Style model

### 4.1 v0.1 persistent Style body

A Style is an ordered list of declarative rules. A rule matches only facts already
exposed by the View Projection and adds named visual roles; it cannot set a colour,
font, coordinate, or token value.

```yaml
version: chrona/presentation/v0.1
kind: style
id: plan-actual
body:
  rules:
    - id: planned-span
      when: { facet: planned, sourceType: span }
      addRoles: [planned]
    - id: actual-span
      when: { facet: actual, sourceType: span }
      addRoles: [actual]
    - id: finish-behind
      when: { facet: finishDelta, category: behind }
      addRoles: [variance-behind]
    - id: actual-missing
      when: { facet: missingActual }
      addRoles: [actual-missing]
```

Rule order is the only v0.1 precedence mechanism: matching rules append roles in source
order, while duplicate roles are removed. `when` is an intersection of its fields;
unknown fields and undeclared facets are diagnostics. This enables a changed Actual to
re-evaluate rules only for its affected View items and emit local `SceneDelta` upserts or
token updates. A rule set has no catch-all code expression and cannot depend on title
text, geometry, renderer state, or local time.

### 4.2 Inputs

A Style receives the semantic View Projection. Its selectors may inspect only stable, declarative facts exposed by that projection, including:

- object kind and identity;
- profile and typed extension fields admitted by the Project schema;
- view membership, grouping, and declared emphasis;
- comparison facets such as `hasActual`, `hasBaseline`, `changedSinceBaseline`, or an explicitly computed plan/actual variance category;
- relationship kind: semantic dependency, explanatory arrow, or annotation anchor.

Selectors must not execute arbitrary host code, mutate the Project, inspect renderer-specific coordinates, or silently obtain data outside the View Context.

### 4.3 Output: visual roles

Style resolves each selected object or relationship to one or more named **visual roles**. Roles describe intent rather than appearance. Representative roles include:

| Semantic subject | Example visual roles |
|---|---|
| Planned work | `planned`, `planned-milestone` |
| Independently observed actual | `actual`, `actual-milestone`, `actual-missing` |
| Snapshot comparison | `baseline`, `changed-since-baseline` |
| Plan-versus-actual comparison | `ahead`, `on-track`, `behind`, `variance-unknown` |
| Dependency | `dependency`, `dependency-critical` |
| Explanatory relationship | `explanatory-arrow` |
| Annotation | `semantic-annotation`, `presentation-annotation` |
| View emphasis | `selected`, `muted`, `focus` |

The closed v0.1 role vocabulary is `planned`, `actual`, `actual-missing`,
`variance-ahead`, `variance-on-track`, `variance-behind`, `variance-unknown`,
`dependency`, `explanatory-arrow`, `semantic-annotation`, `presentation-annotation`,
`selected`, and `muted`. A selector may match only `facet`, `sourceType`, `relationKind`,
and `comparisonCategory`; unknown keys or values are errors. Rules append roles in source
order and deduplicate them; roles never overwrite semantic facts. Conflicting categories
within `variance-*` are an error rather than an implicit last-rule-wins choice.

### 4.4 Plan and actual comparison

Style may make plan-versus-actual differences legible, but it does not calculate schedule truth. The View supplies the aligned Project/Actual references and any comparison facets it has derived under its declared rules. In particular:

- an Actual observation does not reschedule planned work;
- a missing Actual is represented as absence or `actual-missing`, not a fabricated completion;
- an unalignable object produces a diagnostic and `variance-unknown` where it remains visible;
- a baseline difference and a plan/actual difference remain distinct roles, even if a Theme renders them similarly.

This preserves the scheduling model's separation between planned constraints and observed facts.

## 5. Theme model

### 5.1 v0.1 persistent Theme body

A Theme maps the roles resolved by Style to named, concrete tokens. It has no semantic
selector and therefore a token-only edit may emit `tokenUpdate` without recomputing a
View's selection, schedule, or Scene geometry unless the changed token is declared as a
layout metric.

```yaml
version: chrona/presentation/v0.1
kind: theme
id: engineering-light
body:
  values:
    blue-500: {type: color, value: "#3885E5"}
    blue-700: {type: color, value: "#205493"}
    green-500: {type: color, value: "#249B78"}
  roles:
    planned: {fill: blue-500, stroke: blue-700}
    actual: {fill: green-500}
```

`values` declares typed concrete tokens and `roles` binds visual-role properties only to
declared token names. This is the sole v0.1 persistent syntax; the older `tokens` map is
not valid input. A Theme cannot introduce a semantic role, and an unbound or undefined
role/token is a diagnostic.

### 5.2 Tokens

A Theme binds visual roles to concrete tokens. Tokens may describe colour, typography, stroke, fill, marker, opacity, dash pattern, corner treatment, spacing, or accessible text alternatives. A role can resolve to several tokens, and a token can be shared by several roles.

Themes contain no selectors over Project fields. For example, `behind` is chosen by Style; its colour, line treatment, and label treatment are selected by Theme.

### 5.3 Inheritance and resolution

Theme composition is deterministic:

1. a required base theme defines fallback tokens for the standard roles;
2. a named theme may override those tokens;
3. the explicit Render Context selects the active named theme or declared theme variant;
4. unresolved required tokens are diagnostics, not renderer defaults.

A View MUST NOT override concrete token values. A View may expose semantic emphasis for
Style to resolve, but active-theme selection belongs to the explicit Render Context and
concrete token values belong to Theme declarations. This keeps colours, fonts, strokes,
and spacing out of View semantics.

v0.1 Theme has a closed scalar vocabulary: `color` (`#RRGGBB` or `#RRGGBBAA`),
`number`, `fontFamily`, `fontWeight`, `dashPattern`, `marker`, `pattern`, and
`textAlternative`. The Theme declares every token in a named `values` map and each role
binds only declared token names through fixed properties `fill`, `stroke`, `marker`,
`pattern`, `fontFamily`, `fontWeight`, `opacity`, and `textAlternative`. A role binding
may inherit from one named base Theme, but inheritance is resolved base-first, then local
binding per property; cyclic or missing bases and undefined token names are errors.

The resolved output is a concrete scalar map for every selected role. No renderer may
substitute a palette, default font, marker, or pattern when resolution is incomplete.
Style resolution is source-order only; Theme resolution is base-first/property-local.

Specification 29 owns the v0.2 resolved concrete Theme embedded in Presentation
Settings. The one-way chain is `v0.1 values/roles → resolved concrete theme → Scene
paint`. The v0.1 Theme is a legacy authoring resource; it is never supplied alongside a
v0.2 resolved Theme. Scene stores the selected concrete paint and an adapter only
serializes it.

## 6. Accessibility and reviewability

Meaningful distinctions must not rely on colour alone. A standard Theme must differentiate at least planned versus actual, semantic dependency versus explanatory arrow, and exceptional comparison states by a combination of stroke, marker, shape, label, or pattern where colour is insufficient.

Themes and Styles are versioned declarative data. Reviewers must be able to tell whether a changed render is caused by Project facts, View selection, Style role assignment, or Theme tokens. Generated SVG or editor state is an output, not the authoritative place to edit those choices.

## 7. Diagnostics

The following conditions are diagnosable and must not be silently hidden:

- a selector references an unavailable or unsupported semantic field;
- a required visual role has no theme token;
- a comparison role is requested without the corresponding View Context;
- an extension role or token is unknown to the active schema version;
- mutually exclusive role assignments are not resolved by declared precedence.

Diagnostics identify the Style or Theme declaration, the affected semantic object where applicable, and the View Context used for resolution.

## 8. Out of scope

This document does not define:

- YAML/JSON serialization syntax for Style or Theme;
- renderer-neutral scene primitives, text measurement, or coordinates;
- SVG, Canvas, tldraw, or another renderer's API;
- scheduling, progress calculation, resource allocation, cost, timesheets, tickets, or portfolio workflows;
- arbitrary script execution inside selectors.

## 9. Boundary to Scene and Rendering

The next specification resolves styled semantic objects into a renderer-neutral Scene. Scene may choose a rectangle, path, marker, text run, or group and assign concrete coordinates; it must preserve the object's identity, relationship kind, resolved visual roles, and token references. It must not decide whether something is `behind`, a dependency, or an explanatory arrow.

The resulting Scene can be rendered to SVG or used by an interactive editor, but neither output becomes the source of Chrona semantics.

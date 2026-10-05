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
# chrona-contract: historical
version: chrona/style/v0.1
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
# chrona-contract: historical
version: chrona/theme/v0.1
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

`values` declares typed concrete tokens, `roles` binds visual-role properties, and the
optional `metrics` map binds closed semantic metric names to number tokens. This is the
sole v0.1 persistent syntax; the older `tokens` map is not valid input. A Theme cannot
introduce a semantic role or metric contract, and an unbound or undefined role/token is
a diagnostic.

Source adapters use metric bindings such as `text.body.size`, `timeline.row.minBlockSize`,
and `timeline.mark.gap` while measuring and composing one source. Layout Profile distance
fields reference the same reusable number tokens directly. Metric names never select facts
or place source slots; they replace renderer defaults for source-internal visual geometry.

### 5.2 Tokens

A Theme binds visual roles to concrete tokens. Tokens may describe colour, typography, stroke, fill, marker, opacity, dash pattern, corner treatment, spacing, or accessible text alternatives. A role can resolve to several tokens, and a token can be shared by several roles.

Themes contain no selectors over Project fields. For example, `behind` is chosen by Style; its colour, line treatment, and label treatment are selected by Theme.

A `symbol` token's value is either a built-in shape (`diamond`, `circle`, `square`,
`chevron`) or a multi-part glyph (`shape: glyph`, with a `viewBox` and an ordered
`parts` list of SVG path data). Each part paints from the milestone role's own
resolved colour (`paint: fill` or `paint: stroke`) unless the part declares a fixed
`color`, in which case that colour is used instead — except that a role whose own
paint resolves to an outline treatment (`pattern: outline`, typically a baseline
ghost) draws every part as a stroke of the role's own colour and dash pattern,
ignoring any part's fixed `color`. This keeps a baseline variant distinguishable
from its planned/actual variant by shape treatment, not only by colour, even when
every variant shares one glyph asset. `milestoneSymbol` has two optional sibling
roles, `milestoneSymbolActual` and `milestoneSymbolBaseline`, each falling back to
`milestoneSymbol` when unset; a Theme binds a different glyph to one of them only
when a variant needs a different asset altogether (a ghost sprite for a baseline
gate), not merely a different treatment of the same asset.

The #496 asset-catalog successor permits `shape: {catalog: set:name}` on
milestone/gate symbol roles. It resolves only a normalized glyph entry and
then uses the same mark-fit and paint rules above; unknown or wrong-kind
references fail before Layout with `E_THEME_ASSET_REFERENCE` at the Theme
property pointer, including the authored reference. Inline glyphs remain a
valid migration form.

This authoring form is Theme v0.15; derived Theme inheritance is v0.16.
v0.11/v0.12/v0.13/v0.14 are retired after the first-party migration (#1088;
Specification 56 §3.2), not silently upgraded. Theme v0.15 admits
catalog glyph references only on `milestoneSymbol`,
`milestoneSymbolActual`, and `milestoneSymbolBaseline`.

A fill role may select a catalogue pattern through its existing `pattern`
role property, which names a typed pattern token with value
`{kind: catalog, ref: set:name}` when that exact role/property pair is
registered by the Theme applicability contract. The flat fill remains the
opaque representative substrate and the role's resolved stroke is the pattern
ink; catalogue data supplies geometry and density only. Unknown, wrong-kind,
or unregistered bindings fail before Scene construction.
For a catalogue pattern, role `strokeWidth`, `dash`, stroke finish, and gradient
properties are invalid: the catalogue tile supplies its own stroke geometry
and the role fill is a flat substrate. If `backgroundTreatment` is present it
must be `fill`. These conflicts fail at the exact Theme role-property pointer;
they are never silently ignored by Scene or an adapter.
The completed pattern preserves both effective paint channels for
perceptibility and contrast checks; adapters cannot add a fallback color.
Catalogue pattern tokens are admitted only on roles whose current completed
primitive is always Rect: `missing-actual.pattern`, `network-node.pattern`,
`progress-fill.pattern`, `summary-bar.pattern`,
`annotation-highlight-box.pattern`, `axis-band-decoration.pattern`,
`axis-band-decoration2.pattern`, `period-band.pattern` (#582), `group-tab.pattern` (#882),
`as-of-label-chip.pattern`, `member-label-chip.pattern`, and
`finish-delta-chip.pattern`. Other pattern values and all other
role/property pairs retain their current contracts.

**Group tab (#882, #1166).** Theme role `group-tab` declares a tab Rect targeted at group-header text (`tabTarget: header`, the default and today's behavior) or at the vertical group-tag cell (`tabTarget: tag`). `tabTarget` is an optional `header | tag` enum in the live `theme-v0.15` schema (Specification 56 section 3.2); absence preserves existing header output byte-for-byte. A tag target requires `groupHeader.writingMode: vertical`, including when the role is not drawable. Header-only `tabInlineSize`, `tabBlockSize` and `tabPosition` are invalid on a tag target rather than silently ignored. `tabGap` remains a named number token in px: it separates a header tab from its text, while for a tag plate it insets all four sides of the allocated cell. The vertical tag's natural text line-box remains `fontSize × lineHeight`; the allocated column adds `2 × tabGap` so a quarter-turned sideways run fits within the inset plate. A Theme without the role is unchanged. Geometry, failures and contrast are Specification 50 section 3.4.

**Deadline mark (#822).** Theme role `deadline-mark` paints a deadline's tick and run (Spec 06 section 7.3) as Scene
`Path` primitives: `stroke`, `strokeWidth`, `dash` and `opacity` as for `as-of`, plus `markReach` (a named number, `0 < reach
<= 4`: the tick's block extent as a ratio of the planned mark's, centred on it, so a reach above 1 stands above and
below the bar) and `markPaintOrder` (a non-negative integer added to the mark base). The role is required when a View shows
deadlines (`E_THEME_ROLE_REQUIRED`); there is no fallback to another role. Its contrast class is `mark` (3:1, Spec 49), judged
against the ground under each primitive's centre, so a tick that crosses a bar must be visible on the bar and every
primitive on the row ground. `markReach` is added in place to the live Theme schemas (Spec 56 section 3.2).

**Glow (#587).** A role that admits a shadow (Rect, Symbol, Text or Path paint)
also admits `glowColor` (a Scheme binding), `glowBlur`, `glowOpacity` and
`glowFidelity`; the rules, limits, the shadow conflict and the profile ladder are
in Specification 63 section 7.

**Hand wobble (#588).** A role whose completed primitive is a Rect or a Path also admits
`wobbleAmplitude`, `wobbleWavelength`, `wobbleSeed` and `wobbleFidelity`: a deterministic
perturbation of a stroke that changes no bound. It reaches a stroked Rect and a Path, not a
Symbol, Text, Icon, patterned or image-filled Rect, or clip host. The properties are added
in place to the live Theme schemas (Spec 56 section 3.2); the algorithm, limits and the
profile ladder are in Specification 63 section 8.

**Canvas texture (#587).** The Theme role `canvas-texture` paints one catalogue
pattern over the whole completed canvas, below every other primitive. It admits
exactly `pattern` (a `{kind: catalog, ref}` token; an inline pattern kind is
`E_THEME_ROLE_PROPERTY_UNSUPPORTED`), `fill` (the opaque substrate, declared and
never inherited from `background`) and `stroke` (the ink). A role that names no
pattern is `E_THEME_ROLE_REQUIRED` at `/body/roles/canvas-texture/pattern`;
`opacity`, `backgroundPaintOrder`, `strokeWidth`, gradient and shadow properties
are not admitted. A Theme that does not declare the role has no texture and its
output is unchanged. The tile is repeated from the canvas top-left: nothing is
random and no seed exists, so one Theme always renders the same bytes. The
substrate paints over the canvas fill, so a canvas gradient under a texture is
hidden. The texture is ground, not content: it carries no contrast class and no
floor of its own, and marks and state text that lie on it are gated against both
its substrate and its ink (a decoration tint is judged against the substrate).
Typst and TikZ reject it like any pattern. See Specification 08 section 4.0.1.

**As-of light cone (#890).** The Theme role `as-of-cone` paints the light the as-of
marker casts: a polygon from the top of the as-of line, widening downward, fading from
ink to transparent. It admits exactly `fill` (the ink, a Colour Scheme binding),
`opacity` (the strength where the cone leaves the plot top, `0..1`, absent means 1),
`coneSpread` (named number: the half-width the beam gains per unit of depth, a ratio,
`0 < spread <= 4`), `coneExtent` (named number: the depth of the foot as a fraction of
the plot height, `0 < extent <= 1`, 1 reaching the last row) and `gradientFidelity`
(`required` or `decorative-optional`, absent means `required`). A role without `fill`,
`coneSpread` or `coneExtent` is `E_THEME_ROLE_REQUIRED` at that property's pointer; a
value out of range is `E_VISUAL_CAPABILITY_LIMIT` at `coneSpread` or `coneExtent`; any
other property (a stroke, a pattern, `backgroundPaintOrder`, a shadow or glow) is
`E_THEME_ROLE_PROPERTY_UNSUPPORTED`. `coneSpread` and `coneExtent` are optional role
properties of `theme-v0.15` (Specification 56
section 3.2). A Theme that does not declare the role has no cone and its output is
unchanged; the View has no cone switch, and no as-of marker in the window means no
cone. The cone is ground, not content: it carries no contrast class and no floor of
its own, and it is painted above the band grounds and below every mark, the as-of
line and all text whatever a Theme declares (the role admits no paint order). Marks and
state text that lie on it are gated on the ground it makes (Specification 46 section 8).
A profile that cannot paint a gradient omits a `decorative-optional` cone whole and
fails a `required` one (Specification 63 section 9). See Specification 08.

**Region frame (#889, #1165).** A Layout Profile `frame` declaration selects `region-frame`
by default, or `region-frame-<paint>` when its optional `paint` names a shared slug
(Specification 33 section 3). Each selected role independently admits the Rect paint set (`fill`,
`stroke`, `strokeWidth`, `dash`, `opacity`, gradient, shadow, glow and wobble properties), a
catalogue `pattern` (the halftone panel; the pattern closure rule applies, so a patterned role
declares no `strokeWidth`, `dash` or gradient and its `stroke` is the ink), and one Layout
property, `frameCornerRadius` (a named number token, pixels, at least 0). The radius is the radius
of the stroke's centre line and is reduced to half the shorter side when larger
(`W_LAYOUT_REGION_FRAME_CORNER_REDUCED:<node>`). A role with a `fill` is a solid panel (the stroke is
optional); a role with only a `stroke` is an outline panel; a role with neither is
`E_THEME_ROLE_REQUIRED` at `/body/roles/<selected-role>/stroke`. A missing selected role
omits only that frame; it does not fall back to the base role. The role carries no contrast
class: a frame is ground, and what lies on it (a mark, state text, a group header) is gated against its
fill by the ground rule of Specification 46 (completed Scene paint; a frame without a fill is not ground; a translucent fill is
composited over the ground beneath it, #1013). `frameCornerRadius` is added in place to the live Theme
schemas (Specification 56 section 3.2).
`planned`, `actual`, `snapshot`, and `scenario` can emit either Rect or Symbol;
`milestone` emits Symbol; callout/arrow boxes can be balloon Symbols. Catalogue
patterns on these roles require a separate completed Symbol clip/paint design
and are not admitted by Theme v0.15.
`annotation-note-box.pattern` is deliberately not admitted: required note text
uses that box's opaque flat representative fill as its same-source ground under
the #466 contract. A patterned note host requires a separate text-versus-ink
ground policy before admission.

Theme authoring is additionally closed by a role/property applicability
contract. After base inheritance and Color Scheme bindings are resolved, but
before Layout or Scene construction, every declared `roles` property and every
`colorBindings` target MUST have a registered consumer for that authoring role.
The registry distinguishes Layout typography/geometry, Scene paint, and
marker/symbol/contrast policy from the Scene visual-role spelling. A property
with no capable consumer is rejected as `E_THEME_ROLE_PROPERTY_UNSUPPORTED`
with its exact declaration pointer; an unknown role is not accepted merely
because its syntax matches the Theme schema. A role's property may be valid
yet unused by a particular View. A valid decorative treatment unsupported by
the *selected profile* is governed by Specification 63's omission/fidelity
contract instead of this load-time error. The complete selected contract and
resource migration are recorded in the [#478 design](../design/issue-478-declared-treatment-visibility-design-2026-09-26.md).

The [#478 role-admission correction](../design/issue-478-role-admission-rebase-correction-2026-09-27.md)
applies that contract to the current finite role vocabulary. Applicability of
an `annotationContainer` binding is checked on its annotation-box role; the
finite token value and image-catalog asset still follow the existing Theme
schema, `ThemeTokenView`, and Specification 64 closure rules. This admission
gate does not reparse the nested token or move Layout geometry into Scene.

The note annotation roles have explicit contrast responsibilities. The
`annotation-note-text` role is state text and MUST declare
`contrastTreatment: required`; its Theme/Scheme closure is checked against the
4.5:1 state-text floor on the surface the prose lies on, the resolved fill of
`annotation-note-box` (the ground the Scene gate pairs with it; #950), and on
the Scheme surface only when that box declares no readable colour. A Theme may
therefore draw light notes on a dark canvas with dark ink. An ink that fails
against its box is `E_SCHEME_STATE_TEXT_CONTRAST` at the role's `fill`, with the
role and the box named in the detail; the callout, highlight and arrow boxes
are not grounds for note prose. Its completed Scene
paint is checked against its actual declared host ground. The
effective note-text role MUST reject a missing or weaker treatment after
inheritance and Scheme insertion; the generic state-text treatment set does
not relax this note-specific contract. The
`annotation-note-box` role is a decoration and participates in the 1.10:1
decoration visibility policy (a warning below the floor, #995) and corpus witness. These classes are registered
semantic facts, not inferred from the role spelling or paint.

Decoration classification does not imply a `backgroundTreatment` binding.
Only a role that explicitly declares that property has a background-treatment
decision; `none` is an explicit no-draw disposition. A painted annotation
box without the property remains a decoration with an emitted primitive,
not an absent background.

The `annotation-note-box.fill` binding is also the declared representative
content-area color for the note text. For rectangle, balloon, and image-backed
containers, Theme/Scheme closure MUST resolve this representative to opaque
completed paint for contrast/perceptibility use. C4 adds this effective-role
validation after inheritance and Scheme bindings: fill MUST resolve to an
opaque color and opacity (if present) MUST equal 1; otherwise closure fails
with `E_SCHEME_ANNOTATION_NOTE_GROUND` at the offending role property. The
current contrast ground kernel accepts an opaque flat color (including an
image-backed container's declared representative color); it does not sample
artwork pixels. Partial-opacity host composition requires a separate
renderer-neutral ground contract before it can be supported. The new
Scene-level same-source note-box requirement and its unsupported-ground
failure are specified in Specification 08.

For a role name not otherwise registered, the bounded axis-tier measurement
and legend fallback Rect-paint producer families overlap at Theme load time.
The admitted properties are the union of those two potential consumers;
neither producer changes the other's rendering behavior. Known roles retain
their narrower contracts. See the [#478 overlap correction](../design/issue-478-open-role-family-overlap-correction-2026-09-27.md).
Direct role declarations and Scheme-inserted colour targets retain their
respective exact source pointers when applicability fails.

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

**Title and subtitle ink (#1164).** The `heading` and `subtitle` typography roles
MAY bind `fill` and optional `opacity` for their own title line. A fill activates
that line's paint role; without a fill, even an opacity-only declaration keeps
the shared `text` paint unchanged. Layout's measured bounds, lines, baselines,
and font asset identities are independent of this ink choice. `heading.stroke`
is `E_THEME_ROLE_PROPERTY_UNSUPPORTED` at its binding pointer. Both lines are
ground text and use the declared `contrastPolicy.groundText` on their completed
ground. Adapters serialize completed paint and do not resolve these roles.
This addition admits only `fill` and `opacity` on `heading`; it does not enable
the shadow, glow, or gradient effect families on that measurement role.

The next specification resolves styled semantic objects into a renderer-neutral Scene. Scene may choose a rectangle, path, marker, text run, or group and assign concrete coordinates; it must preserve the object's identity, relationship kind, resolved visual roles, and token references. It must not decide whether something is `behind`, a dependency, or an explanatory arrow.

The resulting Scene can be rendered to SVG or used by an interactive editor, but neither output becomes the source of Chrona semantics.

For the versioned [#466 annotation container treatment](../design/issue-466-candidate-placement-design-2026-09-26.md), an authored Theme v0.15 MAY bind a finite `annotationContainer` token to an annotation box role; Theme v0.16 is the derived inheritance representation. The token declares rectangle or balloon outline and tail dimensions, not a position or search. Layout consumes that resolved treatment before placing an annotation, closes the box and tail geometry together, and passes a completed `Rect` for the rectangle or `Symbol` for the balloon outline to Scene; a completed connector is a separate `Path`. Without the binding, a Theme retains its current rectangle/leader output. A View tail candidate requiring a balloon binding is invalid when the Theme cannot supply it; an adapter MUST NOT fabricate one.

For the versioned [#465 image-backed container treatment](../design/issue-465-image-annotation-container-design-2026-09-27.md), the same `annotationContainer` token additionally MAY declare `outline: image`, naming an existing [Specification 64](64-portable-icon-catalogs.md) §7 icon-catalog raster PNG entry (`<set>:<name>`, the same reference form a View uses for an ordinary icon) plus nine-slice stretch insets and a content inset, both in em. Layout measures the annotation's text into the content inset's box and expands it by that inset to the paint box that candidate search and collision use; the nine-slice tile geometry stretched to that paint box is a Layout/Scene fact, never an adapter one. The role's existing fill/stroke colour bindings are unchanged; for an image outline, the fill binding is the Theme author's declared representative colour for the artwork's content area, consumed by contrast and perceptibility exactly as a rectangle's fill is today. A View cannot select or override this binding. Without it, a Theme renders exactly as before #465.

**Contrast policy (#995, #1126).** Contrast constraints are an opt-in design option; they do not bind a Theme that does not ask for them. An authored Theme MAY declare `contrastPolicy` in its body, an object whose members are the classes of finding the completed-Scene gate reports ([Specification 46](46-completed-scene-paint.md) section 8): `mark` (a data mark below 3:1), `stateText` (a state text below its treatment floor), `groundText` (ink on a ground, such as a group header, the as-of label or a member label, below 4.5:1), `decoration` (a decoration below 1.10:1, or on a ground that cannot be read) and `unsupportedGround` (a mark or text on a ground that cannot be computed). Each member is `none`, `warning` or `error`. A member the Theme omits is `warning`: the miss is a typed warning (`W_SCENE_MARK_CONTRAST`, `W_SCENE_STATE_TEXT_CONTRAST`, `W_SCENE_CONTRAST_GROUND_UNSUPPORTED`, `W_SCENE_DECORATION_CONTRAST`, `W_SCENE_DECORATION_GROUND_UNSUPPORTED`) in the render's warnings, the Scene `diagnostics`, the CLI and MCP payloads, and it never fails the render, Theme resolution or the corpus gate. `none` reports nothing; `error` fails the render before any adapter output with the blocking code of the first finding (`E_SCENE_MARK_CONTRAST`, `E_SCENE_STATE_TEXT_CONTRAST`, `E_SCENE_DECORATION_CONTRAST`, `E_SCENE_CONTRAST_GROUND_UNSUPPORTED`) at `/body/contrastPolicy/<member>`. The floors themselves are not Theme values: a class is switched, not retuned. The value `none` is spelled so because an unquoted `off` is a boolean in YAML 1.1. Structural checks (a malformed paint, an invalid treatment, a missing role) and the Theme-resolution text checks are not contrast constraints and are not governed. The member is an optional property of the live Theme schemas (Specification 56 section 3.2; `decoration` gained `none`), validated by the schema and again at Theme resolution (`E_THEME_CONTRAST_POLICY`), and the resolved Theme body carries it. The repository keeps its own guarantee for the Themes it ships by listing them in `conformance/contrast-opt-in.yaml` (Specification 46 section 8), not by editing them.

For the [#584 annotation kind header](../planning/active/issue-584-annotation-kinds-2026-10-02.md), an authored Theme MAY declare `annotationKinds`, an object keyed by the `kind` of a Project annotation (a View annotation reaches it through `projectAnnotation`; an annotation that carries its own text has no kind). Each entry declares a non-empty `label`, an optional non-empty `secondary` label, an optional `title` template and an optional `color`. The `title` template is literal text with the closed placeholders `{label}`, `{secondary}` and `{subject}` (the anchored object's title); `{{` and `}}` are literal braces; any other brace use, an empty `label` or `secondary`, or `{secondary}` without a `secondary` is `E_THEME_ANNOTATION_KIND_TEMPLATE`. The default title is `{label}`. The header is the rendered title in the `annotation-kind-label` text role, then the `secondary` label in `annotation-kind-secondary` as a second line unless the title shows it. `color` is a closed Scheme intent or an explicit `category:<slot>` and resolves at Theme resolution like a colour binding (`E_SCHEME_INTENT_UNKNOWN`); it replaces only the fill of the kind's bar and kind-painted border. A kind the Theme does not declare, and an annotation with no kind, render as a plain annotation. Roles are shared by every kind and each is optional: `annotation-kind-label` and `annotation-kind-secondary` (typography, `fill`, a required `contrastTreatment`), `annotation-kind-bar` (Rect paint and `chipPadding`, the bar's inline padding as a ratio of the label size, half of it on the block axis) and `annotation-kind-accent` (kind-painted border ink; no edge geometry token). Without a label role there is no header and so no bar. Layout grows the note box by the header block (the line heights plus the bar's block padding), widens it to the header when the header is wider than the body, places the bar over the header block and the body text below the header; a bar on a balloon or image outline is `E_LAYOUT_ANNOTATION_KIND_FRAME_OUTLINE`, and header text alone is admitted on every outline. The header text is judged against its real ground: at Theme resolution against each declared kind colour when a bar role exists (the bar's own fill for a kind without a colour), else against every declared annotation box fill (`E_SCHEME_ANNOTATION_KIND_CONTRAST`), never against the canvas surface; the Scene gate reads the completed bar or box under the text. A Theme without `annotationKinds` renders exactly as before.

Kind colour on the header and the leader (#991): an `annotationKinds` entry MAY also declare `colorAlso`, a non-empty list without repeats drawn from `header` and `leader`, and only together with `color` (a malformed list is `E_THEME_ANNOTATION_KIND_TEMPLATE` at `/body/annotationKinds/<kind>/colorAlso`). The kind colour then also paints the header text (both the label and the secondary line, as their fill) and the note's leader line (its stroke) for that kind, beside the bar, accent and stamp it always paints; a kind without the list is today's output. The header text is then judged against the note box as its ground, with the kind colour as its ink (`E_SCHEME_ANNOTATION_KIND_CONTRAST`; a Theme that also declares a title bar of the kind colour fails it, since the text would vanish on its own colour), and Scene's blocking text contrast applies as for any header.
Kind header subject id (#991): the closed header placeholders gain `{subjectId}`, the anchored Project object's id (empty when the anchor is not a selected object), beside `{subject}`, which stays the object's title; a template that omits it is unchanged.

The kind stamp (#584 A584-2) extends the same declaration: an `annotationKinds` entry MAY name a `stamp`, an authored `set:name` reference to a normalized catalogue glyph (Specification 64), resolved through the pinned Context into Layout-completed outline parts exactly as a gate glyph is (an unknown name or set is `E_THEME_ASSET_REFERENCE`). The optional role `annotation-kind-stamp` gives the paint (`fill` for fill parts, `stroke` for stroke parts; the kind `color` replaces the channel each part uses) and `stampPlacement`, a token `{corner: start-top|end-top|start-bottom|end-bottom, size}` whose `size` is the stamp's block size as a ratio of the note text size (the glyph keeps its own aspect). Without the role, or for a kind that names no glyph, there is no stamp. Layout reserves an inline column of the stamp's inline size plus half a text size at the start or end of the note content, over its full block extent and inside the accent edge; the bar, the header text and the body text shrink to the remaining extent, so a stamp never covers text, and the note is at least as tall as the stamp. The stamp stands at the top or bottom of its column. A stamp is admitted on every outline. A glyph with stroked parts carries a required line cap and join, so it needs a visual profile that admits them (Specification 63), like any catalogue glyph.

Slot heading role (#1064): a Theme MAY declare the text role `slot-heading` (the text measurement properties: font family, weight, size, line height, letter spacing, text transform, numeric spacing; and a `slot-heading.fill` colour binding). Layout measures and places every Layout Profile slot heading (Specification 33, slot headings) in it, and Scene paints it with the bound fill; a Theme without the role draws the heading copy in `text`. A heading is ground text for the contrast gate (purpose `slot-heading`): it blocks at 4.5 against the ground under it, so a muted colour that is too faint fails like any other ground text. Font weights are those of the Theme's font assets. A Theme without the role changes nothing for a profile without headings.
Table header role (#991): a Theme MAY declare the text role `tableColumnLabel`. Where it is declared, Layout measures and places every table column header in it (the column minimum, the header baseline and the ellipsis all follow its size, letter spacing and transform), and, when the role also binds a `fill`, Scene paints the headers with it; the cells keep `text` (or `numeric`). A Theme without the role keeps headers in `text` exactly as before.
Table cell and legend text roles (#1062, [work record](../planning/active/issue-1062-text-roles-2026-10-04.md)): a View column's `textRole` names a Theme text role (any name the Theme declares; text measurement properties and `fill`) for that column's cells, and the Theme role `legend` MAY now bind `fill` (and `opacity`) to colour the legend labels, whose size is the role's existing `fontSize`. Where a plain table cell's role binds a `fill`, or `legend.fill` is bound, Scene paints with that role (a Text primitive whose `visualRole` is the role's name); otherwise the `text` ink applies. These inks, like the `tableColumnLabel` header ink, are ground text for the contrast gate: a Text whose role is no registered Scene role is classified by its purpose, blocking at 4.5 on its ground. Adapters serialise the completed size and ink; none reads a role name. A Theme without the declarations, and a View without `textRole`, render exactly as before.
Legend swatch sizing (#1111, [work record](../planning/active/issue-1111-legend-swatch-sizing-2026-10-04.md)): the `legend-swatch` role MAY declare, beside `swatchInlineSize`, the optional absolute number tokens `swatchGap` (at least 0: the distance from a swatch to its label, while the Layout Profile slot `gap` stays the distance between entries; absent, the slot gap serves both, as before), `swatchBlockSize` (above 0: an area key, that is a role outside the mark, point and line keys such as `calendar-closed`, becomes a rectangle of `swatchInlineSize`, else the legacy side, by this block size; absent, the legacy square, so a Theme that declares only `swatchInlineSize` is unchanged) and `pointSwatchSize` (above 0: the side of the gate key; absent, the on-chart gate size). A gap below 0 or a size at or below 0 is `E_THEME_TOKEN_TYPE` at `/body/roles/legend-swatch/<property>`. Legend measurement and drawing read the same values, so the content-sized slot follows them; legend labels stay ground text and no colour changes.
Gate paint (#991): a Theme MAY declare the role `gate` (fill, stroke, strokeWidth, optional pattern; classified as a mark for the contrast and perceptibility gates). Where it is declared, the primary and combined point marks (gates) and the legend's `milestone` key take that role's paint; a baseline or scenario gate keeps `snapshot`, and the mark's purpose, geometry (`milestoneSymbol`, the `planned` mark geometry) and lanes are unchanged. A Theme without `gate` paints gates with `planned` as before. It is a new role rather than the legend-only `milestone`, which bundled Themes already bind.
Role consumers (#1117, [work record](../planning/active/issue-1117-theme-role-consumers-2026-10-04.md)): a role name a Theme declares in `roles` or `colorBindings` must have a consumer. A registered role and a `group:<id>` colour name have one; any other name is read only if a document of the render (the View, Layout Profile, Detail Profile or Summary Profile) carries it, for example as an axis tier `typographyRole`, a column `textRole` or a legend entry `role`. A declaration no document names is reported on every render as the warning `W_THEME_ROLE_UNREAD:<pointer>`, never silently accepted; a Theme shared by several Views may keep a role another View names. `tools/check_theme_role_consumers.py` fails when a non-derived Theme declares a name that no Render Context using it and no bundled preset closure reads.
As-of label ink and typography (#1110, [work record](../planning/active/issue-1110-asof-label-ink-2026-10-04.md)): a Theme MAY declare the role `as-of-label` with the text measurement properties (a `fontSize` makes it a typography role: font family, weight, size, line height, letter spacing, text transform, numeric spacing) and a `fill` (and `opacity`). Where it declares a `fontSize`, Layout measures and sets the as-of label in it, so the label chip's block size, its padding (a ratio of that size) and the block reserved for a `below-plot` chip follow the role; without a `fontSize` the label is measured in `text` as before. Where it declares a `fill`, the as-of label is painted with it, and the contrast gate judges that ink against the label's chip (the chip is the label's own ground); without it the label keeps the `text` ink. `as-of-label` admits no other colour property: a binding such as `as-of-label.stroke` that no primitive reads fails at its pointer with `E_THEME_ROLE_PROPERTY_UNSUPPORTED`.
Note padding (#991): `contentInsetEm` (top, right, bottom, left, in em of the annotation text size) is honoured by every container outline, not only `image`. A rectangle or balloon that declares it measures its text into the smaller box and grows the paint box by the inset, so the text keeps that padding inside the box edge (the kind bar, accent and header sit inside it too); omitted, the inset is zero and the note is today's output. A negative or non-numeric side is `E_THEME_TOKEN_TYPE` at the property; an `image` outline still requires it.
Symbol size (#1066, [work record](../planning/active/issue-1063-1066-target-b-top-items-2026-10-03.md)): a mark role (`planned`, `actual`, `snapshot`, `scenario`) MAY declare the optional number tokens `symbolHeight` and `symbolOffset`, ratios of the track block size like `markHeight` and `markOffset`. They apply to the role's **point** marks (gates and milestones) only: the symbol is a square of side `symbolHeight` times the track at block offset `symbolOffset` times the track, centred on the date, so an `actual` gate can be as large as the planned gate and overlaid on it while the role's bars keep `markHeight`. Each is independent. For `planned`, `snapshot` and `scenario` an absent `symbolHeight` is `markHeight` and an absent `symbolOffset` is `markOffset`. For `actual` the default is the actual gate being no smaller than the planned gate (#1074): an absent `symbolHeight` is the larger of the actual `markHeight` and the planned symbol's height (its `symbolHeight`, else its `markHeight`), and an absent `symbolOffset`, once the symbol is taller than the actual band, centres it on the planned symbol (otherwise it is `markOffset`); a declared value is always kept. Declaring `symbolHeight` equal to the actual `markHeight` and `symbolOffset` equal to the actual `markOffset` restores the earlier thin symbol exactly. `symbolHeight` must be above 0, `symbolOffset` not below 0, and offset plus height at most 1 (`E_THEME_TOKEN_TYPE` for a single value out of range, `E_LAYOUT_MARK_OVERFLOW` for a pair that leaves the track). `missing-actual` is span-only and takes neither. Migration: every slide with an actual gate draws it larger than before unless its Theme declares the restoring pair; baseline ghosts are unchanged.
Note inline size (#1051, [work record](../planning/active/issue-1051-note-inline-size-2026-10-03.md)): the `annotationContainer` token MAY declare `inlineSize`, `content` (the default: the box is as wide as its text, today's output) or `fill`, and, only with `fill`, `maxInlineEm` (a number above 0, in em of the annotation text size). A note whose container declares `fill` and that Layout places on a row-aligned rung of an annotations slot takes the slot's inline size (or `maxInlineEm` text sizes when that is smaller, as a column starting at the slot's start), so such notes share one start edge and one end edge. The body wraps, by the one text measurement and `wrap_text`, in the box inline size minus the leading and trailing visuals, the kind frame's inline insets and the content insets (and any border widths, #1049); an absent `text.wrap` intent means `allow` for a filled note (an explicit `forbid` is honoured), and text keeps its start alignment. Shorter text keeps the full width; longer text wraps and grows the block size. A kind header, an unbreakable word or a `forbid` line wider than the box makes the box that wide (the existing visible-overflow path); text is never clipped. For a tilted note (#584) the rotated bounds, not the unrotated frame, take the slot width. When the note is placed on any other rung, or no annotations slot exists, the box keeps `content` sizing and Layout reports `W_LAYOUT_ANNOTATION_FILL_NOT_SLOT:<annotation id>:<rung>`; nothing fails. `maxInlineEm` without `fill`, another `inlineSize` value or a non-positive maximum is `E_THEME_TOKEN_TYPE` at the property (the schema also rejects it). The sizing is Layout geometry: Scene carries the completed box and lines, so every adapter and visual profile draws it unchanged, and no contrast rule or colour changes. Both properties are optional additions to the live Theme schemas (Specification 56 section 3.2).

Viewer fit (#1050, [work record](../planning/active/issue-1050-viewer-fit-2026-10-04.md)): the SVG names the Layout face (`font-family="Noto Sans, sans-serif"`) and does not embed it (#362), so a viewer that lacks it draws a fallback that can be wider or narrower than the Layout measurement. A box role that carries text, the four annotation box roles `annotation-callout-box`, `annotation-highlight-box`, `annotation-note-box` and `annotation-arrow-box`, MAY bind `viewerFit` to `raw` (the default and absent: today's output, byte for byte), `text-follows-box` or `box-follows-text`, and, only with `text-follows-box`, `viewerFitAdjust` to `spacing` (the default) or `spacingAndGlyphs`; both are inline enums, as `tabPosition` is. On any other role the existing `E_THEME_ROLE_PROPERTY_UNSUPPORTED` applies. A value outside the enum, or `viewerFitAdjust` with another mode, is `E_THEME_TOKEN_TYPE` at the property (the schema also rejects them). **`text-follows-box`:** every text line of the box (the note body and every kind-header line) is pinned to the inline size Layout measured for that line, as drawn (after `textTransform`, at the role's compression, letter spacing included); the pin is the line's own width, never the box's inner width, so a wrapped note keeps its ragged end. Box, collision, leaders and placement are unchanged, and it composes with fill (#1051), border (#1049), artwork (#848), tilt and a kind frame. In a face wider than the measurement a line is condensed to its measured width, in a narrower one it is spaced out to it; `spacing` changes only the gaps between glyphs, `spacingAndGlyphs` also scales the outlines (exact width, distorted shapes). **`box-follows-text`:** the box background ends where the viewer's text ends, so the box is never narrower than its text in any face. It is valid only for a plain, square, untilted, content-sized rectangle: `annotationContainer` with another `outline`, a `cornerRadius` above 0, `tiltDegrees`, `artwork`, `inlineSize: fill` or a `border` side `end`, `top` or `bottom` is `E_THEME_TOKEN_TYPE` at that declaration (`/body/roles/<role>/annotationContainer/<property>`); a start border (#1049) is a separate static strip and is allowed; an annotation with a kind frame or a label visual is `E_LAYOUT_VIEWER_FIT_STATIC_CHROME` at `/annotations/<i>`; a box with a stroke, gradient, shadow, glow, pattern, image or wobble is `E_PRESENTATION_VIEWER_FIT_PAINT` at the role. Nothing is silently degraded. The start inset (content inset and start border) is the pinned start; the end inset is the right content inset, written as a count of the face's own spaces (Layout measures one space and rounds). Layout, collision and leaders keep using the measured box; the painted background may extend beyond it, at the end edge and, in a taller face, the block edges, at view time. A leader attaches to the measured edge. Targets: SVG writes both modes; PNG and PDF draw the packaged font from the `raw` SVG (nothing to absorb); Typst and TikZ draw the static box and lines as `raw` and report `W_VIEWER_FIT_NOT_HONOURED:<box role>:<target>` (Specification 08). Both properties are optional additions to the live Theme schemas (Specification 56 section 3.2).

Viewer fit beyond annotation boxes (#1096): the same `viewerFit` and `viewerFitAdjust` are also admitted on the four label-chip roles (`as-of-label-chip`, `member-label-chip`, `finish-delta-chip`, `period-label-chip`) and on every text role whose runs have no box of their own: `text` (table cells, bar and member labels, the as-of label), `numeric`, `heading` (the title plate), `legend`, `summary`, `metric`, `subtitle`, `tableColumnLabel`, `groupHeader` (vertical group tags), the axis roles and any View-named text role (`tableColumns[].textRole`, #1062). Only `text-follows-box` applies: `box-follows-text` on these roles is `E_THEME_TOKEN_TYPE` at `/body/roles/<role>/viewerFit`, because their text has no box to follow. A label that carries a drawn chip takes its chip role's declaration (a chip role with no chip drawn does not apply); every other run takes the declaration of its own typography role, so a role shared by table cells and bar labels (`text`) pins both, and a View-named role or a chip role separates them. The widths are measured once, after every other Layout decision (ellipsis, wrapping, suppression), in one pass over the completed text; a vertical tag segment is pinned in its own rotated frame. Defaults are unchanged: absent or `raw` produces the same placements, so output is byte-identical. No Theme schema changes (the properties are on every role binding); a role that is neither a text nor a chip role keeps `E_THEME_ROLE_PROPERTY_UNSUPPORTED`.

Annotation box border (#1049, [work record](../planning/active/issue-1049-annotation-box-border-2026-10-03.md)): the `annotationContainer` token MAY declare `border`, an object with any of `start`, `end`, `top`, `bottom` (logical sides; `start` is the inline start edge), each `{width, paint}`: `width` a number at or above 0 in surface units (px, not em) and `paint` `kind` or `ink` (default `ink`). It is admitted on `outline: rectangle`; a `balloon` (its tail is part of the outline) and an `image` (its artwork supplies the frame) are refused by the schema and the token reader (`E_THEME_TOKEN_TYPE` at `/body/roles/<role>/annotationContainer/border`), never ignored; with a `cornerRadius` above 0 the strips follow the rounded outline (#1087, below). The border lies on the outer edge of the box and each side spans the full box side; corners are mitred as in CSS (each side is the trapezoid between the outer edge and the padding edge, an axis-aligned `Rect` when no adjacent side is bordered, otherwise a closed polygon `Symbol`); a side with width 0 or absent draws nothing and takes no space. The content inset is measured from the border's inner edge, so the outer box is content plus inset plus border and the text, the kind frame's content box, the wrap bound (`inlineSize: fill`, #1051: the border widths join the one chrome sum) and the box size all read border plus inset. `paint: kind` draws the strip from the role `annotation-kind-accent` (its fill, replaced by the annotation kind's colour when the kind declares one; the role may be declared with a fill and no `edge`), and `paint: ink` from the role `annotation-border-<side>` (a fill from the colour scheme); a declared side whose role is missing is `E_THEME_ROLE_REQUIRED`. The strips are decorations (`W_SCENE_DECORATION_CONTRAST` below the floor) and never a ground for note text. Paint order is box, vector artwork, border, kind frame, text; a tilted note rotates its strips with its frame. The content-box `edge` declaration is retired (#1088). A Theme migrates its side and size to `border.<side> {width, paint: kind}` and removes the old token and role member; the resulting strip intentionally spans the full outer edge, not the inset content box. `annotation-kind-accent.fill` remains the ink of kind-painted borders, never a second Layout placement. A Theme without `border` renders exactly as before.


Rounded rectangle container (#1087, [work record](../planning/active/issue-1087-rounded-rectangle-container-2026-10-04.md)): a rectangle `annotationContainer` draws its `cornerRadius` (em of the annotation text size, clamped to half the shorter side of the paint box); a value of 0, or no container, is the square box of every earlier output. The paper is a `Rect` with a corner radius, or, for a tilted note, the rotated rounded outline as one closed path of quadratic segments of at most 45 degrees. A `border` follows the outline as in CSS: the padding outline has radii `max(R - width, 0)` per axis (elliptical where the adjacent widths differ, square where either is 0) and each side is the part of the ring between the two outlines, cut at every corner by the mitre line from the box corner to the padding corner, drawn as a closed polygon `Symbol` of arcs. A rounded corner removes paper, so every inset (content inset plus border) is at least `R (1 - 1/sqrt 2)`, which keeps the text, the kind frame and so the contrast ground under them on the paper; this is zero for `R = 0`. Vector artwork (#848) is painted unclipped over the rounded paper, under the border; leaders end on a straight run of the outline (`R <= min(width, height) / 2`); `viewerFit: text-follows-box` composes, and `box-follows-text` stays refused with a radius (#1050: its flood filter paints a rectangle). To restore the square box declare `cornerRadius: 0`.
Calendar-exception paint (#991): a Theme MAY declare the role `calendar-exception` with a `backgroundTreatment` (and `backgroundPaintOrder`, `opacity`, fill and stroke bindings). Where it does, the days the Project calendar closes by an `exceptions` entry (`working: false`) are drawn with it as their own background shapes (`calendar-exception:<date>`, extent and overlay rank as `calendar-closed`), while every other closed day keeps `calendar-closed`; the legend entry whose role is `calendar-exception` keeps its swatch. A Theme without the role (or without a background on it) draws exception days as closed days exactly as before. When the plot is too dense to draw every closed day (`timeline.calendarClosed.minimumDayWidth`), only the exception days are drawn, now in their own colour.

The annotation tilt (#584 A584-3) is a property of the `annotationContainer` token: `tiltDegrees`, a non-empty list of numbers, each within -15 and 15, clockwise in degrees in the surface's frame (the inline axis to the right, the block axis down), admitted only with `outline: rectangle` (a balloon tail and an image's slice tiles do not rotate by this rule; the schema and the token reader reject the combination, `E_THEME_TOKEN_TYPE` at the property). The annotation at position `i` of the View's declared annotations, counted before any placement, takes `tiltDegrees[i mod length]`, rounded to two decimals: a one-element list is a fixed angle, `[a, -a]` an alternation and a longer list a declared cycle, with no random source, hash, clock or iteration order, so two renders are equal. Layout measures the unrotated note frame (box, header, bar, accent, stamp and text) as usual, searches and registers the note through the axis-aligned bounds of that frame rotated about its centre, and, once a position is chosen, rotates every element of the frame rigidly about the centre of those bounds: the box, bar and accent become closed polygons, the stamp keeps its glyph parts with rotated points, and each text keeps its measured lines with its baseline origin rotated and its bounds replaced by the rotated bounding box. A leader still routes to the bounds' port and then continues to the nearest point of the rotated box's edge. A note that carries label visuals cannot tilt (an icon has no rotation): `E_LAYOUT_ANNOTATION_TILT_VISUAL`. An angle of 0, an absent list and a Theme without the property are today's output.

Vector artwork behind an annotation (#848, [work record](../planning/active/issue-848-vector-artwork-container-2026-10-03.md)) is an optional property `artwork` of a rectangle `annotationContainer` token: the existing object `{glyph, sliceInsets, unitEm}` or a non-empty ordered list of layers `{glyph, sliceInsets, unitEm, role?}` (#1167). Each list layer selects `annotation-artwork` by default or explicitly, or `annotation-artwork-<slug>` using the common slug lexeme; other role syntax is `E_THEME_TOKEN_TYPE` at the layer's `/role` member. `glyph` is an authored `set:name` reference to a normalized catalogue glyph (Specification 64), resolved through the pinned Context exactly as a gate glyph is (an unknown name or set is `E_THEME_ASSET_REFERENCE`). `sliceInsets` are the fixed borders `{top, right, bottom, left}`, four non-negative numbers in the glyph's **viewport units**, each opposite pair no larger than the viewport. `unitEm` is a number above zero: the size of one viewport unit in em of the annotation text size. `artwork` is admitted with `outline: rectangle` and `contentInsetEm` only (a balloon, an image outline and a container without the inset are `E_THEME_TOKEN_TYPE` at `/body/roles/<role>/annotationContainer/artwork`; a malformed member, a non-positive `unitEm` or insets larger than the glyph are the same code at the member). Layout measures the text into the content inset as for any container, which fixes the paint box; the artwork never changes that box, the candidate search, the obstacles or the leader. It then stretches each layer's glyph over the same paint box by nine-slice: each fixed border keeps its authored size (its inset times `unitEm` times the text size) and the middle absorbs the rest, so a zero inset lets that border stretch, all four zero stretch the glyph over the whole box, and an inset equal to the glyph's whole extent fixes a strip to one edge and stretches it along the other axis (a clipping edge). A box smaller than the fixed borders of an axis scales both borders of that axis down by one factor. The map is piecewise linear and separable in the two axes; every `L` and `Q` of the glyph is split at each cell boundary it crosses, so each piece lies in one cell where the map is affine and is exact: lines stay lines, quadratics stay quadratics, a hole stays a hole. A stroke part's width scales with `unitEm` times the text size and is not warped, and its cap and join are the glyph's. A nine-slice stretches the cells it declares: a glyph feature in a stretched cell (the scroll's hanger cord, in the top-centre cell) widens with the note, and a glyph authored for stretch avoids it. The box keeps painting the paper under the artwork; each layer's parts are ink from its selected role (the legacy object's role is `annotation-artwork`) (`fill` for fill parts, required as for any solid role; `stroke` for stroked parts; `opacity`; and `artworkFidelity`, a `fidelity` token, default `required`). An undeclared selected role is `E_THEME_ROLE_REQUIRED`: the legacy object retains `/body/roles/annotation-artwork`, while a list layer reports `/body/roles/<container-role>/annotationContainer/artwork/<index>`, including an omitted role whose default is absent. The order is the box (the paper), the artwork layers and their parts in declaration order, the border and kind frame (accent, bar, stamp), then all text, so the artwork lies under the bar, the stamp and every line. A tilt cycle (#584) rotates the artwork rigidly with the note; the kind bar and accent, rectangle-only, compose with it. The text is judged on the paper and on any artwork ink it touches (Specification 46 section 8) and the artwork against the paper as a decoration. Under a visual profile that cannot paint a stroked part (no line cap and join, as the baseline), `artworkFidelity: required` fails with `E_VISUAL_CAPABILITY_UNSUPPORTED` and `decorative-optional` omits the whole affected layer and reports it, independently of other layers even when they select the same role (Specifications 08 and 63); a fill-only glyph needs no omission. The legacy object retains its geometry, primitive identities, diagnostics and output; a container without `artwork` renders exactly as before.

A text role MAY compress its text horizontally (#585 I585-1) by binding `horizontalScale` to a `number` token, like `letterSpacing`; it is admitted on every role that admits typography. The value is within 0.5 and 1 inclusive (compression only: below the floor a face is no longer the same face, and an extension is a different treatment); outside it is `E_THEME_TEXT_SCALE_RANGE` at `/body/roles/<role>/horizontalScale` with the value as detail, raised at Theme resolution for every declared role, used or not, and again by the token reader; a non-number token is `E_THEME_TOKEN_TYPE`. Absent and 1 are today's output. Layout measures the compressed width: the scale enters once, at the metric Layout selects for the role, and multiplies the whole run width, letter spacing included, so every fit, wrap, ellipsis, column and box decision sees the compressed text; the em height, line height and baseline are not changed, and a quarter-turn or tilted run is compressed along its own reading direction. It is a transform of the face, so vertical stems are thinner than a designed condensed face; no packaged face has a width axis and none is measured from one.

A text role MAY be written vertically (#585 I585-2) by binding `writingMode` to a token of the type `writingMode` whose value is `horizontal` or `vertical`; absent is horizontal. Only the group-label role `groupHeader` supports it: on any other role the existing `E_THEME_ROLE_PROPERTY_UNSUPPORTED` applies, and a `horizontalScale` other than 1 on the same role is `E_THEME_TEXT_TREATMENT_CONFLICT` (a horizontal squeeze has no defined meaning on a vertical inline axis). Vertical here is a single column read top to bottom, as CSS `vertical-rl` with `text-orientation: mixed`: after `textTransform`, the label is cut into segments. **Upright** characters stand alone, one em apart: hiragana and katakana (U+3041-30FF), CJK ideographs (U+3400-4DBF, U+4E00-9FFF, U+F900-FAFF), Hangul syllables (U+AC00-D7AF), CJK symbols and punctuation (U+3000-303F) and fullwidth forms (U+FF01-FF60), centred in the column by their measured width. **Sideways** is everything else (Latin, digits, ASCII punctuation, spaces, any other script) and also, by exception, the prolonged sound mark U+30FC, the wave dashes U+301C and U+FF5E, the dashes U+2014 and U+2015, the ellipsis U+2026 and U+2025, and every bracket (CJK, fullwidth and ASCII): the vertical form of these glyphs is the horizontal glyph turned a quarter turn. A maximal run of sideways characters is one segment, turned a quarter turn clockwise (the tops of the letters point right) and advancing by its measured width. `letterSpacing` is added after every segment but the last. The column's inline size is the role's `fontSize` times `lineHeight`. Limits, stated: no OpenType `vert` substitution (so `、` and `。` keep their horizontal-text cell position), no tate-chu-yoko (a digit run is sideways), no kerning, one column, start alignment. With `grouping.presentation: header`, a vertical `groupHeader` replaces the horizontal header row: no header row is reserved, and Layout carves a tag column of that inline size from the start of the table slot (columns, cells and hierarchy indent are laid out in what remains; bands and stripes keep their extents). Each group's tag spans the rows of its group from the top of the first to the bottom of the last, with half an em of clear space at each end; a label longer than that span is cut at the last segment that fits and ends with a sideways ellipsis (`overflow: ellipsized`, the source text kept). It applies to automatic and lane rows alike. The default (horizontal) and `presentation: band` are today's output.

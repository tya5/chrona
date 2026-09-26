# Intent-Oriented Layout

**Status:** Design complete; implementation not started.  
**Owns:** The single author-facing composition grammar, its resolution algorithm, and
the resolved Layout Manifest.  
**Supersedes:** The `layout-profile/v0.1` prototype grammar/runtime and the layout
authoring fields of `presentation-settings/v0.2`. There is no compatibility path.

## 1. Outcome and authority

Layout expresses relationships, not coordinates. A profile composes named presentation
sources into a tree, refers to Theme-owned number tokens for ordinary distances, and is
resolved using declared viewport and measurement inputs. The result is a Layout
Manifest containing derived rectangles, baselines, references, and diagnostics.

The authority boundary remains:

| Layer | Authority |
|---|---|
| View | selected facts, grouping, ordering, window, logical annotation anchors, repeated-source definition |
| Style | semantic fact-to-role selection |
| Theme | concrete typography, paint, symbol, and number tokens including spacing |
| Layout | composition tree, sizing policy, alignment, distribution, bounded relative placement |
| Render Context | viewport, locale, writing mode override when declared, immutable resource and metric inputs |
| Scene | resolved source-linked primitives and coordinates |
| Output adapter | serialization only |

Layout MUST NOT select Project facts, calculate schedules, define colors/fonts, invent
metrics, persist authoritative coordinates, or branch on a profile ID.

## 2. Resource and reuse model

The canonical resource is `chrona/layout-profile/v0.4` as defined by the replacement
schema. A resource contains exactly one of:

- `root`: a complete layout tree; or
- `extends` plus `overrides`: an immutable base Layout Profile reference and stable-node
  partial overrides.

There is no array-index patch syntax. Every node ID is unique over the resolved tree.
An override key names one existing node ID. An override may replace declared properties
of that node but cannot change its ID, kind, or insert executable content. Unknown IDs,
base cycles, kind changes, null deletion, and multiple bases diagnose.

Whole Layout Profiles are the reusable composition unit. Theme resources are the
reusable value unit. Render Context binds separate immutable Theme and Layout resource
references to a Project, View, optional Detail/Summary/Actual inputs, viewport, locale,
metrics and target. Complete aggregate settings are an internal resolved value, not an
authoring file or referenced authority.

## 3. Composition grammar

The root is a container. Containers are:

| Kind | Rule |
|---|---|
| `row` | Lay children along the logical inline axis. |
| `column` | Lay children along the logical block axis. |
| `grid` | Place children into explicit tracks/cells; every direct child declares `cell`, and no implicit anonymous tracks exist. |
| `flow` | Place children in source order and wrap at the declared available inline bound. |
| `overlay` | Give children one shared coordinate space; normal children use `place`, anchored children use bounded anchor rules. |

A leaf has `kind: slot` and consumes one declared presentation source. Closed initial
sources are `title`, `table`, `timeline`, `timeline-axis`, `summary`, `legend`,
`group-details`, `observations`, `milestones`, `annotations`, and `notes`.

`facet` and `repeat` are not M24 layout operators. View may expose a typed repeated
source, which Layout can arrange with `grid` or `flow`; Layout cannot partition facts.

## 4. Logical axes and writing mode

Normative directions are logical:

- inline: `inline-start` to `inline-end`;
- block: `block-start` to `block-end`.

Profile `writingMode` is `horizontal-tb`, `vertical-rl`, or `vertical-lr`. Render Context
may select a declared supported mode but cannot silently substitute one. Physical
`left`, `right`, `top`, and `bottom` are not grammar values.

Alignment values are `start`, `center`, `end`, `stretch`, `first-baseline`, and
`last-baseline`. Baseline values require measured baseline data and diagnose when the
participating source cannot supply it. Container distribution values are `start`,
`center`, `end`, `space-between`, `space-around`, and `space-evenly`.

## 5. Size and distance values

Each node declares `inlineSize` and `blockSize`. A size is one of:

- `content`, `min-content`, `max-content`, or `fill`;
- `{fr: positive-number}`;
- `{fixed: distance}`;
- `{fitContent: distance}`;
- `{minmax: {min: size, max: size}}`;
- `{aspectRatio: positive-number}` on exactly one axis when the other axis resolves.

`fr` is a proportion of remaining space, not an absolute coordinate. `content` and its
variants require intrinsic measurements. `fill` participates in equal distribution of
remaining space after fixed, intrinsic, bounded, gap and padding requirements.

A distance is either a non-negative finite number or `{token: name}`. Built-in and
acceptance profiles MUST use token references for margins, padding, gaps, and ordinary
clearance. A numeric distance is permitted only as an explicit optical/export bound and
is recorded in the manifest as a literal. There is no implicit `10000` infinity value;
an absent maximum means unbounded within the declared viewport.

## 6. Placement, overflow, and distribution

Every slot declares `place.inline` and `place.block`. Containers declare `alignItems`
for the cross axis and `justifyContent` for the main axis. A slot value overrides its
container's item alignment on that axis.

`stretch` changes only an `auto`/`fill`-compatible used size; it never violates a fixed,
intrinsic minimum, or maximum. `safe` placement falls back from center/end to start when
that avoids unreachable overflow. `strict` retains the requested alignment when it
fits. If valid measured content cannot fit, both modes complete visible natural
placement and warn under Section 13; neither turns a fit shortage into an error.

Required content may use only `diagnose` or `ellipsize-with-source` overflow. Optional
content may additionally use `clip-optional`. Ellipsized or omitted output retains full
source text and the decision in Scene metadata.
The legacy `diagnose` slot spelling does not override Section 13 for a valid
fit shortage. Exact text-plus-icon compositions keep both components and
grow visibly if even a declared compact representation cannot fit.

## 7. Anchors, guides, and barriers

Relative placement is allowed only for a child of `overlay`. An anchor contains:

- `self`: inline and block points on the child;
- `target.inline` and `target.block`: independent `parent`, `node:<id>`, `guide:<id>`,
  or `barrier:<id>` references plus one point on that axis;
- optional `gap.inline` and `gap.block` logical distances.

Points are `start`, `center`, `end`, `first-baseline`, or `last-baseline`. An axis may
target a guide/barrier only when that object declares the same axis. A node may therefore
use the inline end of a content barrier while independently using the block center of its
parent. Gaps are applied away from the target edge on their named axis; a
center-to-center axis cannot declare a gap. There is no raw x/y offset.

A guide belongs to one overlay, has an inline or block axis, and is positioned at
`start`, `center`, `end`, or a rational fraction string such as `1/3`. A barrier belongs
to one overlay, names at least one descendant node, and resolves to the start or end
extreme of their measured/arranged bounds on one axis. Barrier members cannot depend on
that barrier. Cross-overlay references and references to descendants outside the same
resolved profile diagnose.

## 8. Deterministic resolution

### 8.1 Source measurement and composition boundary

Each closed presentation source has one adapter with two pure operations. `measure`
receives the resolved source value, resolved Theme, declared font metrics, locale, any
resolved immutable icon metrics, and an optional available inline bound, and returns
min/preferred/max logical sizes plus available baselines. `compose` receives the same closed inputs and exactly one resolved Layout
Manifest rectangle and emits source-linked Scene primitives inside it.

Source adapters may read View-owned semantic modes and Theme `metrics` bindings. They may
not read Layout YAML, resize or move their slot, allocate peer slots, or supply fallback
coordinates. Every author-tunable source-internal distance is a Theme number token reached
through a closed semantic metric name. A missing binding or non-number token diagnoses;
there is no renderer default table. Layout source measurements are collected once, frozen,
and reused by arrangement and Scene composition so the two passes cannot disagree.

The initial metric contract is namespaced by source/component (`text.*`, `table.*`,
`timeline.*`, `axis.*`, `legend.*`, `notes.*`, `icon.*`). The adapter owns the closed key set and
rejects unknown keys in its namespace. View owns grouping, comparison, visibility,
wording, and semantic icon choice; Theme metrics own only concrete visual quantities.
For an icon-leading label, Layout reserves the resolved icon width and gap before text
measurement, then records separate icon/text bounds and the text baseline in its completed
placement. Scene and adapters may not recompute that reservation or placement.

Resolution uses the following ordered passes:

1. validate resource shape and immutable references;
2. resolve `extends`, then apply stable-node overrides;
3. resolve Theme tokens and reject missing/non-number distance tokens;
4. collect declared source measurements (`min`, `max`, preferred size, first/last
   baselines) without guessing;
5. measure the tree bottom-up;
6. constrain and arrange normal-flow containers top-down;
7. resolve overlay guides, provisional member bounds, then barriers;
8. topologically resolve anchored overlay children;
9. apply safe alignment/overflow rules and collision policy;
10. emit the canonical Layout Manifest or stable diagnostics.

Stable node ID breaks otherwise equivalent source-order ties. Decimal calculations use
the implementation's specified decimal context; manifest coordinates are quantized only
once at the declared Scene precision. Hashes use canonical JSON key ordering, never
Python `repr` or YAML presentation order.

### 8.1 Accepted prerequisite: one surface obstacle contract

The [#466 design](../design/issue-466-general-placement-design-2026-09-26.md)
defines the successor for annotation and plot-label placement. Layout creates
one typed surface obstacle inventory and grows it monotonically as marks,
routes, labels, annotation boxes and connectors are completed in declared
finite phases. Every placement and leader query names the same inventory,
relevant obstacle classes, a finite region and only explicit host/port
exemptions. Dependency paths are stroke-segment obstacles, not their broad
enclosing rectangles. Scene receives completed decisions and geometry, never
an obstacle query. A later design completion must define the exact candidate
grammar, chosen-candidate evidence and bounded search before legacy rungs
are normalized to candidate data. The obstacle-only prerequisite may publish
before nearest-free and tail support; those remain incomplete until their own
design and release gates pass.

## 9. Diagnostics

The implementation exposes at least:

| ID | Condition |
|---|---|
| `E_LAYOUT_SCHEMA` | Resource fails the replacement schema. |
| `E_LAYOUT_BASE_CYCLE` | `extends` cycle. |
| `E_LAYOUT_OVERRIDE_UNKNOWN` | Override names no resolved node. |
| `E_LAYOUT_OVERRIDE_KIND` | Override attempts to change node kind or ID. |
| `E_LAYOUT_NODE_DUPLICATE` | Duplicate stable node ID. |
| `E_LAYOUT_SOURCE_UNAVAILABLE` | Required slot source is unavailable. |
| `E_LAYOUT_TOKEN_UNKNOWN` | Referenced Theme token is missing. |
| `E_LAYOUT_TOKEN_TYPE` | Distance token is not a non-negative number. |
| `E_LAYOUT_MEASUREMENT_REQUIRED` | Intrinsic/baseline size lacks declared measurement. |
| `E_LAYOUT_REFERENCE_UNKNOWN` | Anchor, guide, barrier, or member reference is unknown. |
| `E_LAYOUT_REFERENCE_SCOPE` | Relative reference crosses its overlay scope. |
| `E_LAYOUT_CONSTRAINT_CYCLE` | Anchor/barrier dependency cycle. |
| `E_LAYOUT_CONSTRAINT_CONTRADICTORY` | Authored constraints are structurally contradictory independently of viewport size. |
| `E_LAYOUT_BASELINE_UNAVAILABLE` | Baseline alignment lacks compatible baseline data. |
| `E_LAYOUT_REQUIRED_OVERFLOW` | Retired for a valid current fit shortage; historical diagnostic only. |

Diagnostics include profile ID, node ID when applicable, and a resource path. They do
not include renderer-selected recovery coordinates.

Annotation leaders resolve their View-owned object/facet/endpoint anchors to
completed mark-boundary ports before routing against the shared surface
obstacle inventory. A route may exempt its specifically named endpoint port,
not its entire host mark or row. `body` chooses the nearest outline point
toward the selected annotation box with a deterministic side tie order.
Visible direct-route fallback is a stroked segment obstacle even if diagonal;
later placements must account for it. See the [#466 anchor-port correction](../design/issue-466-general-placement-anchor-port-correction-2026-09-26.md).

A measured rule label may exempt only its own named rule stroke during its
placement; the rule remains an obstacle for other labels and annotations.
See the [#466 rule-label correction](../design/issue-466-general-placement-rule-label-correction-2026-09-26.md).

Semantic relations also use completed route-specific boundary ports. A point
glyph's central mark anchor is not a routable port; Layout chooses a finite
outline tip toward the other endpoint and exempts only that named port when
routing. See the [#466 point-relation-port correction](../design/issue-466-general-placement-point-relation-port-correction-2026-09-26.md).

When a point/body tip is blocked by a comparison sibling or another required
obstacle, Layout tries the remaining finite ports in stable distance/side
order and accepts the first bounded quality route. Failed port candidates do
not suppress the relation or enter the obstacle inventory. See the [#466
point-port-candidate correction](../design/issue-466-general-placement-point-port-candidate-correction-2026-09-26.md).

A semantic endpoint covered by its own same-row comparison marks retains its
date and may use a finite, recorded corridor to the comparison-host boundary.
Only those named siblings are exempt on that corridor; the route after egress
queries the entire inventory. See the [#466 comparison-egress correction](../design/issue-466-general-placement-comparison-egress-correction-2026-09-26.md).

Text measurement precedes allocation, but optional plot-label *placement*
follows semantic dependency routing. Required text and rule labels enter the
shared obstacle inventory before relations. Accepted relation segments then
constrain optional plot/item/delta labels, followed by relation labels and
annotations. This finite monotone phase order prioritizes visible semantic
connections without allowing label/route overlap or changing declared route
quality and overflow limits. See the [#466 route-priority correction](../design/issue-466-general-placement-route-priority-correction-2026-09-26.md).

## 10. Layout Manifest

The canonical manifest records:

- profile and Theme content identities;
- viewport, writing mode, metric identities, and Scene precision;
- resolved tree and stable node/source mapping;
- for each node: bounds, intrinsic inputs, used sizes, alignment/distribution decisions,
  token references and literal-distance provenance;
- resolved guides, barriers, anchors and fallback decisions;
- diagnostics and optional-content omissions.

The same closed resources and inputs MUST produce byte-identical canonical manifest
bytes and equivalent Scene geometry. Output adapters consume Scene, not the profile.

## 11. Replacement and deletion

Implementation installs `schemas/layout-profile-v0.3.schema.yaml`, deletes the v0.1
schema when the v0.2 runtime becomes reachable, and replaces
`chrona.presentation.layout.solver` rather than adding a legacy branch. The `surface`
bag, named margin/density lookup tables, header/footer name branches, `repr` hashes,
insertion-index slot allocation, and implicit `1400×900`/`10000` values are removed.

The layout portion of complete Presentation Settings is removed from authoring. Values
that are truly Theme choices remain Theme tokens; detail wording remains Detail;
viewport/locale/metrics remain Render Context; composition moves only to Layout.
Obsolete conformance fixtures and tests are rewritten, not kept as compatibility tests.

## 12. Acceptance invariants

1. A centered node re-centers after viewport or measured-content changes without profile
   edits.
2. A barrier follows the widest member and an anchored peer follows the barrier.
3. Row/column/grid/flow/overlay examples contain no authoritative coordinates.
4. Built-in examples contain no literal routine spacing.
5. One stable-ID override leaves all unspecified base nodes unchanged.
6. Constraint cycles, missing measurements, unknown tokens/references, and
   structurally contradictory bounds diagnose before Scene claims completion.
   A shortage against an otherwise valid measured allocation completes a
   visible placement and warning under the fit-completion rule below.
7. Layout changes do not alter Project/Schedule/Actual/View facts.
8. Human and AI proposals use the same schema, resolver, solver, and manifest.
9. No old layout schema/runtime/settings authority remains reachable.

## 13. Fit completion (Issue #457)

For a valid Layout Profile and positive viewport, normal-flow measurement and
arrangement MUST complete finite placements even when fixed tracks, content
minima, padding, or cross-axis geometry exceed the requested viewport. Layout
keeps measured natural sizes, records typed `W_LAYOUT_VISIBLE_OVERFLOW`
warnings with placement identity and required/available extents, and grows the
completed canvas as necessary. A fit shortage is not
`E_LAYOUT_CONSTRAINT_CONTRADICTORY` or `E_LAYOUT_REQUIRED_OVERFLOW`.
The completed canvas includes any emitted geometry before its requested origin
as well as geometry beyond its requested end; the adapter uses that completed
viewBox without independently repositioning primitives.
Malformed profile constraints and invalid references remain errors. Scene and
adapters MUST NOT resolve this shortage independently.

### 13.1 Content-coherent table-timeline allocation (#468)

For a table-timeline surface whose measured row/track content has a finite
required block extent, Layout MUST apply that requirement to the normal-flow
allocation before composing surface placements. The requested viewport is a
minimum. Layout re-solves the complete profile at a sufficient finite block
extent so the review-surface, table and timeline hosts grow together and
later siblings such as notes move below them. Merely expanding the completed
canvas around rows while leaving their known hosts and later siblings at the
old positions is not a valid completion. If an otherwise valid profile fixes
or caps a host so it cannot grow, Layout retains natural visible fallback and
typed shortage warnings under Section 13; it MUST NOT claim that host grew.
This rule applies equally to Draft and immutable table-timeline closures.
An attempted larger extent is committed only if its final LayoutManifest
actually satisfies every declared content-host requirement. A fixed/capped
profile that cannot do so retains the requested finite allocation and the
ordinary visible fallback; a speculative larger canvas without added host
capacity is not a valid reallocation.

Draft ingress defaults to an inline extent of 1600 and a content-resolved
block extent (`1600xauto` in the CLI). Draft closure still carries a finite
seed before Layout resolves the final allocation; no `auto` value is stored
in an immutable Render Context. Explicit finite Draft extents and immutable
Context extents remain valid minimum requests.

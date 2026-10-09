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

A `legend` slot additionally declares `direction` (`block` stacks entries; `inline`
flows them along the inline axis) and `gap` (space between entries, and between a
swatch and its own label), and may declare `itemMinInlineSize` when `direction:
inline`, wrapping exactly as a `flow` container wraps its children (#427). Each
entry's swatch is constructed by the same geometry its role's `primitive_kind`
already uses for an object mark, relation, or decoration; Layout never derives a
swatch's shape or size from the legend label's typography role.
The `legend` source measures the entries it will draw: each entry's natural inline size
is its swatch, the item gap and the drawn label (a colour-scale entry with the entity
title, not the raw value), a `block` legend is as wide as its widest entry, and an
`inline` legend as wide as the line of entries, or as the widest entry when
`itemMinInlineSize` lets it wrap. Measurement and drawing use the same entries and the
same swatch geometry (#497).
The [#427 dispatch amendment](../design/issue-427-legend-swatches-design-amendment-2026-09-26.md)
qualifies this rule: known mark/line/decoration roles use the closed
chart-matching dispatch, while an otherwise unregistered legend role retains
a fixed-square Rect swatch painted by its own role. The [#478 admission
amendment](../design/issue-478-legend-role-admission-amendment-2026-09-27.md)
therefore admits only portable Rect paint for an otherwise unregistered
legend-only name; it cannot make an unsupported property on a known text or
relation role valid.

**Region frames (#889, #1165).** Any container, any slot and any override may declare `frame`, with
optional `inset` (a `distance`, default 0) and `paint` (the shared `common-v0.1` slug).
Absent `paint` selects `region-frame`; a name selects `region-frame-<paint>` without fallback.
A frame is a request to draw a panel behind the node;
it adds no space and moves nothing. The engine arranges the whole profile first and records the frame
with the node's completed bounds and whether the node holds a slot of positive area (`populated`); Layout
then completes one Rect per drawable frame from those facts. The Rect is the node's bounds deflated on
every side by `inset` plus half the selected Theme role's stroke width (Specification 07), so
the outer edge of the stroke stands `inset` inside the node and never spills into the gap or past the
canvas. The space *between* two panels is what a profile already declares: the parent's `gap`, plus both
insets (between outer stroke edges); the space *inside* a panel is the framed container's `padding`. A
frame whose node holds no slot of positive area (a panel around only absent optional sources) or whose
deflated Rect has no area is not drawn, and Layout records `I_LAYOUT_REGION_FRAME_OMITTED:<node>:<no-content|too-small>`;
a Theme that does not declare the selected role omits only that frame and fails nothing. Layout completes frames in
the profile's pre-order (a container's panel before its children's), and the canvas grows to contain each
frame's whole stroke. An override replaces a node's `frame` wholesale and cannot remove one. The
declaration is checked before the schema so an error is named at its exact pointer (`E_LAYOUT_SCHEMA` at
`/root/children/0/frame` or `.../frame/inset` or `.../frame/paint`, `/overrides/<id>/frame/...`); an `inset` token follows the
distance-token rules of section 5. Only the table-timeline surface draws frames; the dependency-network
surface ignores the declaration.

The same declaration independently selects `frame-glyph[-<paint>]` (#888,
Specification 07), even without a panel role. Layout contain-centres upright
catalogue glyphs in `glyphSize` squares, reserving the completed stroke envelope
inside `inset` (Specification 46 section 7). Emit four unique corners, then
clockwise top/right/bottom/left interiors. An edge's centre span `L` has
`floor(L / glyphPitch)` equal intervals, distributing the remainder; either
span shorter than the pitch omits the whole border. No populated content also
omits it, with `I_LAYOUT_FRAME_GLYPH_OMITTED:<node>:<no-content|too-small>`.
Each node's panel precedes its one completed glyph batch, parents before
children; Scene never fits the run or changes content allocation.

**Slot headings (#1064, [work record](../planning/active/issue-1065-1064-field-group-indent-and-slot-heading-2026-10-04.md)).**
A slot whose `source` is any enumerated slot source, and an override of such a slot, may
declare `heading: {text, align, block}`: a caption over the slot. This includes the native title, table,
timeline, timeline-axis, dependency-network, group-details, milestones and observations owners as well as
annotations, notes, legend and summary. `text` is literal presentation copy (one to
eighty characters, no control character; the Theme role's text transform styles it, so a profile holds "Notes"
and a Theme makes it "NOTES"); `align` is `start` (default), `center` or `end` within the slot's inline
extent; `block` is `top` (default), `header-row` or `axis-tier`. The engine records the declaration with the slot's bounds;
Layout completes one Text `slot-heading:<node id>` in the Theme text role `slot-heading` (the role `text` when
the Theme declares none), inside the slot. The line box is the role's font size times line height and the gap
under it half the font size. At `top` the line starts at the slot's block start. At `header-row` the line box
is centred in the `timeline-axis` slot's band when that band's block extent intersects the slot's (it lies
beside the slot; otherwise `top` applies and Layout records `I_LAYOUT_SLOT_HEADING_NO_HEADER_ROW:<node>`).
At `axis-tier`, the caption baseline equals the primary baseline of the uppermost horizontal labels tier
(completed block position, then tier index) in that neighboring axis. Layout exports its measured tier
geometry independently of visible or thinned labels; band-only and rotated tiers are not targets. The
content starts below the whole axis band and any larger caption line/gap. Without a compatible neighboring
tier, or when that aligned caption line cannot fit inside its slot, `top` applies and Layout records
`I_LAYOUT_SLOT_HEADING_NO_AXIS_TIER:<node>`; the baseline is never clamped while claiming tier alignment.
The slot's content starts below the line and its gap, and below the band when the caption sits in it, so nothing
lies under the caption; the slot keeps its full bounds. The native owner then lays out its content in that
reduced viewport: title runs, table/timeline rows, axis tiers, dependency-network geometry and detail-panel
content each retain their existing owner and placement rules. A content-sized slot (`blockSize: content`)
measures the caption's block into its size only when its selected source has content; intrinsic measurement
and caption completion use the same semantic presence decision. For shared table/timeline rows, the native
table-header and axis prefix are measured for the exact candidate before allocation, and the row floor starts
after the greater of that prefix and the caption-reduced content start. A fixed or filling slot gives the
caption part of its allocation. A caption never moves another slot.
A slot with no area, one too short for its caption, or one whose source has no content draws no caption and
reserves nothing (`I_LAYOUT_SLOT_HEADING_OMITTED:<node>:<too-small|no-content>`); an absent optional slot has
no decision and so no caption. A caption wider than the slot is cut with its source kept
(`W_LAYOUT_TEXT_ELLIPSIZED`). A derived profile overrides the copy with `overrides: {<slot>: {heading: ...}}`
(the whole declaration is replaced). A View may override only the caption copy with `slotHeadingText`
(Spec 06 §7.5), keyed by the resolved slot node ID. This leaves the profile, hash, allocation, alignment,
block placement and caption reservation unchanged; Layout measures and completes the selected copy.
All enumerated slot sources accept a heading; a malformed heading is `E_LAYOUT_SCHEMA` at its exact pointer.
For `timeline-axis`, semantic presence is its normalized nonempty axis-tier declaration; an empty axis omits
the heading and adds no content-sized caption reserve.
Absent declarations leave output and manifest bytes unchanged.

### Heading source claims (#1239)

A slot source of `heading` is a whole-block alias for the existing `title` source. It is
canonicalized to `title` after profile validation, so the resolved source identity and
whole-heading output remain unchanged. `heading.title`, `heading.kicker`, and
`heading.subtitle` select one part of the View-resolved heading and retain that part's
existing typography role. A whole-block claim (`title` or `heading`) claims all three
parts; an individual source claims only its named part. No part may be claimed twice.
Duplicate or overlapping claims, including claims introduced through resolved base
overrides, fail with `E_LAYOUT_SCHEMA` at the later slot's `/source` pointer and name
the already-claiming slot and part.

Heading-part sources remain valid even when their optional content is empty; required
priority does not synthesize copy. Layout omits a placement for an empty part. If a
nonempty part has no slot claim, Layout omits it and records
`I_LAYOUT_HEADING_PART_OMITTED:<part>`; an empty unclaimed part is silent. The legacy
`title` whole-block claim remains the default and keeps its prior composition path.
Only claimed parts require typography measurement; unclaimed copy remains available
for omission notices without requiring an unused role. Dependency-network's legacy
whole-title host still ignores View heading templates (Spec 06); a profile without
that host opts into the View-resolved parts. Part placements carry their measured
bounds, baseline, typography and explicit slot owner directly into Scene.

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

A flexible track's (`fr` or `fill`) used size is resolved by CSS Grid's own iterative
"find the size of an `fr`" procedure (#487, ADR-0032), not a single-pass formula: a
flexible track's `minmax` minimum is a floor its share must clear, never an amount its
share is added underneath.

1. `fr` is the space available to the flexible tracks in the same container, still
   unassigned, divided by the total weight of the flexible tracks still unresolved. This
   set starts as every flexible track and the full flexible-track space (computed once,
   before any flexible track's own minimum is subtracted from it) and shrinks each round.
2. Any unresolved track whose own resolved minimum (`0` unless it declares
   `{minmax: {min: …}}` with a nonzero minimum) exceeds `fr` times its weight is fixed at
   that minimum, removed from the unresolved set, and its minimum is subtracted from the
   unassigned space.
3. Step 1 repeats until no unresolved track's minimum is violated at the recomputed `fr`.
4. Any unresolved track whose declared `minmax` maximum is smaller than `fr` times its
   weight is fixed at that maximum the same way, and step 1 repeats again for what is
   left unassigned.
5. Every track still unresolved once no minimum or maximum is violated gets `fr` times
   its weight.

This resolves the total unassigned space exactly, never oversubscribing the container:
a single-pass `max(minimum, share)` computed once per track independently is **not**
equivalent, because a track fixed at a minimum larger than its one-shot share does not
reduce what the *other* tracks still take, and the total can then exceed what is
available. It leaves every flexible track whose minimum is `0` unaffected, since it can
never violate a minimum (`0 > fr × weight` is false for `fr ≥ 0`) and so always reaches
step 5 with the same result a purely additive rule would have given.

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
source text and the decision in Scene metadata. A text that Layout shortens with an
ellipsis always carries a typed `W_LAYOUT_TEXT_ELLIPSIZED` fit warning naming the
primitive, its natural inline size and the inline size it had (#497); `ellipsize-with-source`
declares that an ellipsis is allowed, never that it may be silent.

A slot whose inline or block size is `content` resolves to the measured natural size of
its source. When its `overflow` is `ellipsize-with-source` and its composer shrinks and
reports that shrink (the `legend` source), the used cross-axis size is bounded by the
container, so a content-sized slot is as large as its widest entry up to the space its
container offers. Any other slot keeps growing past its container and warns
`W_LAYOUT_VISIBLE_OVERFLOW` under Section 13.
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

**Publication status:** the O1/O2 shared-obstacle prerequisite passed its
[public artifact and CI gate](../reviews/current/issue-466-shared-obstacle-prerequisite-acceptance-review-2026-09-26.md).
The later candidate search and balloon behavior is a separate successor
contract, not a claim that it has already been implemented.

The [#466 design](../design/issue-466-general-placement-design-2026-09-26.md)
defines the successor for annotation and plot-label placement. Layout creates
one typed surface obstacle inventory and grows it monotonically as marks,
routes, labels, annotation boxes and connectors are completed in declared
finite phases. Every placement and leader query names the same inventory,
relevant obstacle classes, a finite region and only explicit host/port
exemptions. Dependency paths are stroke-segment obstacles, not their broad
enclosing rectangles. Scene receives completed decisions and geometry, never
an obstacle query. The [#466 candidate design](../design/issue-466-candidate-placement-design-2026-09-26.md)
defines the successor grammar, chosen-candidate evidence and bounded joint
box/connector search. Legacy rungs normalize to that data without a visual
change; nearest-free and tail support require their own release gates.

### 8.1a Candidate model

A candidate has exactly the four declared parts `region`, `search`, `obstacles`,
and `connector`, plus a stable ID. Layout resolves a finite region after slot
allocation and tests measured box and connector together against the one
monotone obstacle inventory. Plot search MUST avoid marks, text, label visuals,
dependency and earlier leader strokes, annotation boxes, ports and rules; an
as-of rule partitions plot search on the anchor side. Search is deterministic
and bounded. The decision records the chosen candidate ID and joint-trial
count. A later candidate fit warns with its chosen ID. Exhaustion follows
explicit suppression or the existing visible-overflow completion, never a
hidden new placement mode. The exact versioned View grammar and tail Theme
treatment are in the linked design; Scene and adapters only project completed
geometry.

### 8.2 Annotation connector topology after the shared inventory

The [#466 connector correction](../design/issue-466-annotation-connector-topology-correction-2026-09-26.md)
is the accepted successor contract for O2, not a claim that current `main`
implements it. Layout MUST evaluate each annotation box and its connector as
one provisional candidate. A fit commits both atomically to the same surface
obstacle inventory. A failed pair MUST NOT leave provisional obstacles behind.

Strict connectors avoid all declared obstacles. A rail leader MAY use an
explicit, bounded bridged-orthogonal topology after strict search. A bridge
MAY cross only a prior leader or semantic dependency stroke, transversely and
away from junctions/endpoints. It MUST NOT cross a mark, text, annotation box,
port other than a named endpoint, or rule barrier. Layout completes a visible
gap in the later annotation connector at each crossing; the crossed stroke
remains continuous. The connector remains a single source-linked placement,
and Scene/adapters MUST NOT decide the crossing or gap. A tail connector MUST
use strict topology. For a nearest-free balloon, Layout MUST try the integrated
direct tail first. If blocked, it MAY complete a strict local orthogonal route
to a short exterior balloon tip. The route, tip and pending balloon body MUST
clear the same obstacles together, including the body's interior, and stay on
the anchor's as-of side. Layout records `direct-tail` or `routed-tail` and
commits box, outline and route atomically. Scene/adapters only project the
completed geometry. See the
[#466 C3 correction](../design/issue-466-c3-routed-tail-correction-2026-09-29.md).
The local search corridor, route quality, crossing count,
and exhaustion are bounded and recorded in the placement decision. If all
declared candidates fail, an explicit suppress outcome or the visible
fallback policy applies; fallback MUST NOT be reported as a collision-free
fit. The later candidate grammar will specify the public spelling of these
policies. The local corridor is based on the source mark and selected box
attachment point, not the full box extent; see the
[#466 corridor amendment](../design/issue-466-connector-corridor-amendment-2026-09-26.md).

When a hosted annotation number refers to a Theme glyph mark, Layout MUST
resolve its abstract mark host to an actual emitted lane-facet primitive ID
before Scene projection. The host identity and paint order are completed
placement facts; Scene MUST reject a missing host rather than infer a glyph
part. See the [#466 host correction](../design/issue-466-c3-hosted-note-index-correction-2026-09-29.md).

### 8.3 Surface implementation ownership (#592)

These private modules divide Layout implementation only; they do not change authoring contracts or §1 authority. `surface_composer` coordinates phases and final assembly. Obstacle users retain the one ordered index and phase order in §§8.1a–8.2.

| Module | Layout responsibility |
|---|---|
| `surface_base` | Validate closed inputs; compose slots, rows, base group extents, scale and tracks. |
| `surface_table` | Place table columns, headers and cells. |
| `surface_groups` | Place group-header text and group presentation from completed base extents. |
| `surface_axis` | Place axis bands/labels and targets; derive calendar overlay intervals from the completed scale. |
| `surface_marks` | Place tracks/marks/folded points/progress. |
| `surface_member_labels` | Build requests and place member/item labels. |
| `surface_lanes` | Adapt/preflight fixed lanes; emit lane facets and close host identities. |
| `surface_lane_route_plan` | Plan the route corridors member names must keep clear by rehearsing the name and route phases on private index copies; return corridors only. |
| `surface_route_label_plan` | Coordinate one optional member-name recovery trial; return the selected completed route/label batches and their matching index without replay. |
| `surface_routes` | Place dependency paths/ports and relation labels. |
| `surface_annotations` | Place annotation boxes, text, visuals and connectors. |
| `surface_legend` | Place legend entries and role-derived swatches. |
| `surface_observations` | Measure and place native observation tables, attributed source lines and row cells inside their content slot. |
| `surface_heading` | Project closed heading measurements and baselines into title-slot text placements. |
| `surface_content` | Place detail, summary, notes and footer source content. |
| `surface_backgrounds` | Complete source-bound row/group/axis/calendar background geometry from completed extents and overlay intervals. |
| `surface_periods` | Complete named-period band geometry (#582) from the View-selected periods, the completed scale and the Theme treatment; clip to the window and plot and record a period with no extent. |
| `surface_deadlines` | Complete a deadline tick and, for a slipped deadline, a run to the planned finish (#822) from the View-shown deadlines, the completed planned marks, the scale and the Theme reach; record a deadline outside the window or on a folded header point. |
| `surface_visuals` | Reserve and place text/mark/axis label visuals. |
| `surface_completion` | Complete slot ownership, overflow evidence, canvas bounds, lane row anchors and catalogue patterns for final Rect shapes and span marks, and assemble the final placement. |
| `surface_geometry` | Pure rectangle/date conversions and shared precision/paint-order constants. |
| `surface_composer` | Invoke typed phase batches in order and construct final Layout output. |
| `surface_preparation` | Close candidate-specific inline, heading, axis, table-header and shared row-floor geometry before row placement; derive natural demand and final host admission from the same measured prefix. |

Each module owns its named concern and reads closed inputs plus preceding typed Layout results; shared mutable surface state is limited to the obstacle index. The policy coordinators use private index copies: `surface_lane_route_plan` returns only rehearsed corridors, while `surface_route_label_plan` returns the selected completed batches and their matching index under the bounded recovery rule below. `surface_legend` and `surface_content` complete named sources in allocated slots outside obstacle-candidate phases; fixed host backgrounds complete when their extents are known. The #466 phase order governs obstacle-sensitive candidates, not these placements. Ownership names guide internal issue coordination and are not public import contracts. Module moves themselves preserve behavior and introduce no placement policy.

The calendar join has one direction: `surface_axis` returns ordered closed-date intervals and axis facts; `surface_backgrounds` converts those intervals into Theme-treated shapes at the current calendar insertion phase. A folded mark may enlarge a completed group-header host. `surface_marks` returns the replacement group extent as a typed fact, and `surface_backgrounds` applies that fact to the already placed header band with a pure replacement operation; the coordinator retains the established emission order. No module duplicates the other's placement or mutates a shared group/shape collection across phases.

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
An endpoint MAY additionally authorize registered, exactly coincident port IDs
belonging to the same named connected comparison-host cluster. The authorized
IDs are resolved before the route query and recorded; unrelated or non-endpoint
ports remain obstacles. See the [coincident-egress amendment](../design/issue-466-coincident-egress-port-amendment-2026-09-26.md).
When an already accepted connector leaves the same port, a later connector
MUST try finite exterior fanout stubs rather than overlap the earlier stroke;
the complete route, including the stub, remains subject to obstacle and
quality checks. See the [shared-port fanout amendment](../design/issue-466-shared-port-fanout-amendment-2026-09-26.md).
Annotation connectors first test a bounded sparse elbow family before the
bounded dense visibility grid. Both use the same obstacle inventory, local
corridor, and route-quality policy; the first feasible path is deterministic
but need not be globally shortest. See the [sparse-search amendment](../design/issue-466-sparse-elbow-route-search-amendment-2026-09-26.md).
Resolved Theme line widths contribute to registered stroke obstacles and
Layout-completed bridge gaps. Endpoint-only opposite-direction contact is
legal; positive-length collinear overlap is not. Sparse/dense bounds and
internal search accounting are specified in the [clearance precision
amendment](../design/issue-466-connector-clearance-precision-amendment-2026-09-26.md).

A measured rule label may exempt only its own named rule stroke during its
placement; the rule remains an obstacle for other labels and annotations.
See the [#466 rule-label correction](../design/issue-466-general-placement-rule-label-correction-2026-09-26.md).

Semantic relations also use completed route-specific boundary ports. A point
glyph's central mark anchor is not a routable port; Layout chooses a finite
outline tip toward the other endpoint and exempts only that named port when
routing. See the [#466 point-relation-port correction](../design/issue-466-general-placement-point-relation-port-correction-2026-09-26.md).

When a point/body tip is blocked by a comparison sibling or another required
obstacle, Layout tries the remaining finite ports in stable distance/side
order and selects an eligible route using the relation ranking in
[Spec 50](50-constraint-driven-gantt-surface-quality.md#33-relations).
Failed port candidates do
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

If this order suppresses a post-route member name, Layout may make one private
feasibility retry: place only the lost-name requests using their unchanged
declared ladders, then route and place the remaining labels. Select that
completed trial only if it strictly reduces the lost-name set, preserves every
relation identity without degrading its status, and loses no relation-label
identity. Otherwise retain the normal route-first result and its diagnostics.
Reuse the chosen completed batches and inventory; do not replay or iterate the
winning branch. This recovery does not waive safety or route-quality limits.

Fixed-lane member names and selected deltas are the route-independent
exception: their finite candidates resolve after lane geometry but before
semantic relations, and only accepted labels enter the route obstacle set.
Their terminal suppression is counted without altering membership (Specs 38
and 50). Relation labels still follow their completed routes.

After canonical side candidates fail, optional plot/item/delta and relation labels may use
a finite side-relative displacement with at most 512 actual collision queries.
Member-name candidates are bounded by the row and the completed own marks'
existing association reach, accounting for measured Text dimensions and insets;
the exact nearest-perimeter association check remains mandatory. A redundant
one-label-width displacement limit must not exclude an otherwise associated
name. Other labels retain their measured-footprint displacement bounds.
After canonical positions fail, displacement candidates
include obstacle-contact coordinates and exact footprint/row edges as well as
the regular lattice, so a narrow legal interval is not skipped solely by an
8px sampling step. Rank candidates deterministically by displacement and side
order; all still satisfy their placement and association bounds.
This fallback never changes the declared side, never
ignores accepted route strokes, and leaves required and annotation placement
unchanged. Relation labels retain their completed longest-segment anchor and
canonical side order before this bounded fallback. See the [#466 side-search correction](../design/issue-466-general-placement-side-search-correction-2026-09-26.md).

Member-label collision queries use completed span paint footprints, including
half the resolved stroke width outside semantic bounds. This reuses the lane
facet footprint without changing relation ports or body obstacles. Query
snapshots do not own accepted placements: every accepted label enters the
single shared inventory before the next request is queried.

An annotation's optional note-number index and required leader are separate
Layout outputs. If the index cannot fit, Layout diagnoses and omits only the
index; the accepted annotation box/text and purpose-required leader remain.
See the [#466 index/leader correction](../design/issue-466-general-placement-note-index-leader-correction-2026-09-26.md).

**Numbered annotation list status (#1130, [archived work record](../archive/planning/issue-1130-note-index-suppression-2026-10-04.md)).**
When the Layout declares an `annotations` slot, its ordered note list is a
separate output from each annotation's plot index and callout box. Every numbered View annotation retains its View-order
ordinal and visible content. When an optional plot index is
suppressed, the accepted note text remains and the rail visibly says `index
not shown on plot`; the index-suppression diagnostic remains, and any required
leader remains connected to its accepted box. For a rail-located note, include
the status in its list entry and recomplete its rail geometry. For a
plot-located callout, keep the original body, kind frame, box and leader
geometry; place a separately measured, ordinal-keyed status in the declared
annotations slot. Do not resize a plot callout to display list bookkeeping,
or suppress its required leader because that status enlarged its body.
Independent status and summary records use `annotationListText` semantics:
free rail text on its actual ground, not boxed `annotationNoteText` prose
(Specification 08). Original note prose retains its required box contract.
When the annotation callout box/leader is suppressed,
Layout retains a compact numbered summary entry visibly saying `callout not
shown on plot`; the existing callout-suppression diagnostic remains, and no
plot index, box, or leader is fabricated. These statuses are Layout-derived,
not View/Project facts or adapter decisions. Layout measures and places the
final list entries after resolving plot visibility; it may not renumber them
or repair a completed Scene in an adapter. When suppression adds a summary or
status, entries may reflow in View order within the declared slot; Layout
must recomplete affected boxes and required leaders against the obstacle
inventory, never move text alone or revive a suppressed plot callout.
Reflow may additionally suppress an index or callout that no longer fits,
but never restores either once suppressed in that composition. Repeat only
when the suppressed identity set strictly grows; this bounds visibility
transitions by the finite annotation/index inventory and prevents stale status.
In the no-suppression case, the
existing Scene and adapter output remain byte-identical. This preserves
intentional callout suppression while preventing a silent numbering gap.
Without that slot, Layout does not fabricate a list or change the existing
plot-only annotation behavior. List overflow must remain explicitly diagnosed,
never silently omit an entry.
If a new status or summary has no non-overlapping position in the declared
slot, place it after preceding rail records in View order and mark its text
as `visible-overflow`, with the existing label-overflow diagnostic. Do not
clamp multiple required records onto the same fallback position or silently
grow the canvas. The author controls sufficient slot capacity.

Segment/rectangle obstacle tests treat a `1e-9` layout-unit boundary contact
as contact, not interior penetration; a longer positive interior crossing
remains blocked. This handles floating representations of the same completed
port/mark edge without changing clearance or route policy. See the [#466
boundary-precision correction](../design/issue-466-general-placement-boundary-precision-correction-2026-09-26.md).

The proposed outer-envelope route fallback is **not accepted** for product
behavior: it passed geometric quality limits but failed rendered connector
quality on controller-z. The [#466 topology design plan](../planning/active/issue-466-annotation-route-topology-design-plan-2026-09-26.md)
must resolve connector/annotation placement interactions before O2 release.

## 10. Layout Manifest

The canonical manifest records:

- profile and Theme content identities;
- viewport, writing mode, metric identities, and Scene precision;
- resolved tree and stable node/source mapping;
- for each node: bounds, intrinsic inputs, used sizes, alignment/distribution decisions,
  token references and literal-distance provenance, and its region frame (`inset`, `populated`) when
  one is declared (#889; a manifest without a frame is byte-identical to before);
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
Footer successor completion uses every completed native footer line,
including wrapped notes, preserves the allocated successor gap, and occurs
before annotation placement; no-growth or inline-disjoint successors remain
unchanged.

Draft ingress defaults to an inline extent of 1600 and a content-resolved
block extent (`1600xauto` in the CLI). Draft closure still carries a finite
seed before Layout resolves the final allocation; no `auto` value is stored
in an immutable Render Context. For a Draft `auto` request, that synthetic
finite seed is required for closure validation but MUST NOT become the lower
bound of the final content-sized result. Layout MUST select the least
positive integral logical viewport block extent that satisfies the measured
natural table-timeline content requirement and the complete resolved
normal-flow profile, including intrinsic profile minima, measured title,
axis, legend and note content, margins, and normal-flow spacing. Satisfying a
content host alone is insufficient when another normal-flow placement or
profile minimum requires more extent. The final LayoutManifest allocation
MUST verify the selected extent; overflow added only to the completed canvas
does not count as satisfying this allocation. The selected extent is rounded
upward to a whole scene unit. When there are no table-timeline rows, the
content-sizing floor is one scene unit; any larger intrinsic profile
requirement controls the result.
Natural normal-flow measurement MUST use the same track allocation rules as
final arrangement: grid row-track bases are summed with gaps and padding;
only single-span children contribute to those bases under the current grid
allocation rule, while multi-span shortage retains its visible fallback.
Flow uses lines at the resolved inline extent, a flow item is measured at the
inline extent it is arranged at (its natural width, never shrunk to the line:
section 13 keeps natural sizes and diagnoses the overflow), so a content-sized
nested flow wraps the same way in measurement and in arrangement (#1206), and anchored overlay
decoration does not enlarge the normal-flow minimum. A fixed or capped track
contributes its declared capacity rather than a promise to absorb more
content; its shortage follows the visible fallback above.

Explicit finite Draft extents and immutable Context extents remain minimum
requests and MUST NOT shrink below the requested block extent. If measured
content requires more space, Layout re-solves the complete normal-flow
profile at the least sufficient finite extent. If a valid profile fixes,
caps, or anchors a content host so that it cannot gain the required capacity,
Layout retains the requested finite allocation and its natural visible
fallback and typed shortage evidence; it MUST NOT claim that the host grew,
treat completed-canvas overflow as successful reallocation, manufacture
extra blank allocation, or refuse an otherwise valid render. The completed
canvas still includes emitted geometry as required by Section 13.

For content-sized allocation, the measured natural per-row and table-timeline
requirements MUST be established before `rowDistribution: fill` distributes
remaining space. Fill MUST consume only the actual surplus in the selected
final timeline host, and fill-expanded row placements MUST NOT become an
input to a subsequent content-sizing pass. Explicit larger minimum requests
may therefore create surplus for fill, while a compact auto result places
rows at their natural requirements.

## 14. Seeded canvas tiles and overlay geometry (#888)

The `seeded` pattern declaration (Spec07) is a bounded Layout program. It
completes existing `PatternPlacement` data: angle 0, top-left canvas phase,
canvas region/clip, corner radius 0, and primitives in motif declaration order.
No Scene or adapter runs a generator. Both surfaces use the completed canvas,
not the initially requested viewport. Texture and overlays never enlarge it.

`splitmix64-v1` uses unsigned arithmetic modulo `2**64`. For draw index `j`
starting at 0, let `z = seed + (j + 1) * 0x9E3779B97F4A7C15`; then
`z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9`,
`z = (z ^ (z >> 27)) * 0x94D049BB133111EB`, and
`z = z ^ (z >> 31)`, masking each integer result to 64 bits. The draw is
`(z >> 11) / 2**53`. Exactly two draws per motif select inline/block position;
no scene identity, hash, dictionary order, runtime randomness or trigonometry
participates. This version is independent of future wobble algorithm changes.

All arithmetic uses IEEE-754 binary64. Quantization is `round(value, 3)`:
nearest 0.001px on the represented value, ties to even (not multiply-then-round).
Reject nonfinite inputs before rounding; round physical tile/motif dimensions
before positive-domain and fit checks. Completed geometry must remain finite
and nondegenerate after position quantization/clamping. Grain is a filled circle of the declared
radius, with centre independently uniform in `[radius, extent - radius)`.
Rain is one butt-capped stroked line with block displacement `length` and
inline displacement `slant * length`, centred uniformly within the tile
after reserving half its displacement and half the stroke width on each side.
Both available centre ranges must be positive; a motif cannot cross its tile.
Selected centres are rounded to 0.001px and clamped to their centre ranges;
rain endpoints are rounded to 0.001px and clamped to the half-stroke inset tile.
Invalid or collapsed dimensions/fit are `E_THEME_TOKEN_TYPE` at the selected
role's `pattern` binding, not a partial tile. Density is the ceiling of the
summed motif-area upper bound as basis points of tile area, clamped to
`[1, 10000]`; actual ink geometry, not this bound, decides contact.

Layout completes radial centre as canvas origin plus the declared centre
fractions times canvas extents, and radii as radius fractions times those
extents. The stop offsets are 0, the declared inner stop when greater than 0,
and 1. Scene adds colour and opacity without deriving spatial geometry.

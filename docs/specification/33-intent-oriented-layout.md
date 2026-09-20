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

The canonical resource is `chrona/layout-profile/v0.2` as defined by the replacement
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
that avoids unreachable overflow. `strict` placement diagnoses rather than changing the
requested alignment.

Required content may use only `diagnose` or `ellipsize-with-source` overflow. Optional
content may additionally use `clip-optional`. Ellipsized or omitted output retains full
source text and the decision in Scene metadata.

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
receives the resolved source value, resolved Theme, declared font metrics, locale, and an
optional available inline bound, and returns min/preferred/max logical sizes plus available
baselines. `compose` receives the same closed inputs and exactly one resolved Layout
Manifest rectangle and emits source-linked Scene primitives inside it.

Source adapters may read View-owned semantic modes and Theme `metrics` bindings. They may
not read Layout YAML, resize or move their slot, allocate peer slots, or supply fallback
coordinates. Every author-tunable source-internal distance is a Theme number token reached
through a closed semantic metric name. A missing binding or non-number token diagnoses;
there is no renderer default table. Layout source measurements are collected once, frozen,
and reused by arrangement and Scene composition so the two passes cannot disagree.

The initial metric contract is namespaced by source/component (`text.*`, `table.*`,
`timeline.*`, `axis.*`, `legend.*`, `notes.*`). The adapter owns the closed key set and
rejects unknown keys in its namespace. View owns grouping, comparison, visibility, and
wording choices; Theme metrics own only concrete visual quantities.

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
| `E_LAYOUT_CONSTRAINT_CONTRADICTORY` | Fixed/bounded requirements cannot fit. |
| `E_LAYOUT_BASELINE_UNAVAILABLE` | Baseline alignment lacks compatible baseline data. |
| `E_LAYOUT_REQUIRED_OVERFLOW` | Required content cannot be placed under its policy. |

Diagnostics include profile ID, node ID when applicable, and a resource path. They do
not include renderer-selected recovery coordinates.

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

Implementation installs `schemas/layout-profile-v0.2.schema.yaml`, deletes the v0.1
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
6. Constraint cycles, missing measurements, unknown tokens/references, contradictory
   bounds, and required overflow diagnose before Scene claims completion.
7. Layout changes do not alter Project/Schedule/Actual/View facts.
8. Human and AI proposals use the same schema, resolver, solver, and manifest.
9. No old layout schema/runtime/settings authority remains reachable.

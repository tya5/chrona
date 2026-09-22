# Issues 259, 278, and 279: Completed Design

## Status and scope

This document completes the design planned in
`issues-259-278-279-design-plan-2026-09-23.md`.  It intentionally makes no
implementation change.  The delivery order is #259, #279, then #278.  Each
change remains independently reviewable and mergeable.

The design is based on public `main` at `f259ba0`: View owns selected review
semantics, Layout owns completed geometry, Scene projects that geometry into
the closed primitive vocabulary, and renderers serialize primitives without
reopening View, Project, or Layout decisions.

## #259: one reproducible contributor test contract

`pytest` exercises renderer conformance, whose installed Python dependencies
are the `render` extra.  The documented command therefore becomes:

```console
python -m pip install -e '.[dev,render]'
python -m pytest
```

`dev` remains the developer-tool extra and `render` remains separately named:
this avoids silently making runtime render libraries a requirement for every
library consumer.  README, CONTRIBUTING, and CI use the same extra set.  The
acceptance condition is that a fresh environment running the documented two
commands completes the documented suite, including public-materializer tests.

## #279: semantic rounded geometry

### Theme vocabulary and defaults

The Theme metric vocabulary gains three optional, non-negative metrics:

* `timeline.mark.cornerRadius` for span marks;
* `timeline.point.cornerRadius` for point/diamond marks; and
* `timeline.relation.cornerRadius` for dependency routes.

Absent bindings mean `0`; an explicit `0` is valid.  Positive values are
resolved by the existing measured-source/Theme boundary and are never read by
a renderer from raw Theme resources.  The first two values are clamped by
Layout to the relevant completed mark bounds.  A route value is clamped at each
turn by its two adjoining orthogonal legs.  Existing Themes stay byte-stable
because they omit all three metrics.

The metrics deliberately name the semantic family, not `Rect`: group bands,
calendar closure, axis decoration, annotation boxes, legend swatches, and
summary bars remain square unless a later design gives them their own policy.

### Typed handoff

`MarkPlacement` gains an explicit mark form (`span` or `point`) and a resolved
corner treatment.  `RelationPlacement` gains completed path geometry rather
than an instruction for a renderer to round a route.  A compact
renderer-neutral path-command value represents move, line, and rounded-turn
segments.  Layout derives those commands from the already-routed orthogonal
polyline and its clamped radius.  `ScenePrimitive` receives the completed mark
corner treatment and path commands verbatim.

With a zero point radius, Scene continues to emit the existing diamond Symbol,
preserving current outputs.  With a positive point radius, Layout supplies a
rounded-diamond path and Scene emits that completed Path primitive.  This is
necessary because a diamond cannot consume SVG `rx`, and prevents SVG polygon
syntax from becoming a hidden geometry owner.  Span marks remain Rects with a
semantic radius.  Relation arrowheads retain their existing marker semantics;
only their route geometry changes.

SVG serializes span radius as `rx`/`ry` and the completed route or
rounded-diamond commands as path data.  TikZ serializes the same command
sequence as explicit path/curve geometry.  Typst either serializes the same
path form supported by its target or rejects an unsupported non-zero rounded
path with a stable renderer-capability diagnostic; it must not silently emit a
square substitute.  Renderer tests cover all three targets and both zero and
positive values.

### Invariants and evidence

Layout rejects negative or non-finite values, emits only clamped radii, and
ensures every rounded Path has a valid command sequence and the same start/end
ports as its underlying route.  Scene has no metric lookup, corner arithmetic,
or route transformation.  Tests prove that only semantic mark primitives get
mark rounding; they also inspect SVG for `rx`/`ry`, rounded diamond path data,
and non-mitred relation turns.  Opted-in example Theme fixtures and regenerated
SVG evidence demonstrate all three independent controls.

## #278: automatic point-fold policy

### View contract

Automatic rows gain an optional `points` policy:

```yaml
rows:
  mode: automatic
  points: own-row | group-header | predecessor
```

Omission and `own-row` retain the current one-selected-object/one-row result.
The option is illegal in explicit mode.  It affects only selected point objects;
spans and non-point objects retain normal automatic rows, selection, ordering,
grouping, window calculation, and comparison facets.

`group-header` requires `grouping.presentation: header` and a plot label
configuration containing `title`.  A folded point deliberately receives no
table cell; its required identity remains its label on the header target.  A
missing header-capable group or a non-visible title label is a typed View
diagnostic, not an implicit own-row fallback.

`predecessor` places a point on a selected span's automatic row only when it
has exactly one eligible incoming Project relation.  An eligible predecessor is
selected, has span source type, and has exactly one addressable automatic row.
Zero, multiple, point, hidden, or otherwise unavailable candidates produce an
explicit own row and a deterministic warning diagnostic.  This conservative
fallback preserves materializability while making the inability to fold
inspectable.  The Project relation's canonical identity is used for ordering
and evidence; Scene never discovers predecessors.

### Projection representation

The View projection gains a typed `FoldedPointProjection`, separate from
`ReviewRowProjection`.  It carries the selected point item, its stable
projection-instance identity, and a target of either a normal review row or a
group header.  A predecessor-folded point is appended as a shared-track member
to the target review row, while retaining its own instance identity and
comparison facets.  A group-header-folded point is not fabricated as a table
row and does not overload `ReviewRowProjection` with a null table subject.
Instead, the projection preserves it as a header-targeted folded item.

This distinction is structural: a group header is a group decoration with a
real Layout extent, not a fake object row.  It avoids blank table cells and
keeps table-content composition responsible only for rows with a table subject.

### Layout, Scene, and relations

Layout first allocates normal rows and group-header extents.  It then assigns
tracks for normal members and separately assigns deterministic header tracks
within the completed GroupPlacement header bounds.  The header label and folded
point labels share the header collision domain.  Mark ports, labels, routes,
annotations, and relation obstacles are built from the resulting completed
placements regardless of whether their owner is a row or a header.

Scene projects those placements and their semantic identities only.  It does
not choose a fold target, synthesize a table row, allocate a header track, or
reroute a relation.  The existing table-content builder skips header-targeted
items.  A relation endpoint remains addressable by the folded point's stable
instance ID, so folding does not make dependency routing ambiguous.

Planned, actual, snapshot, and scenario variants remain members of the same
selected point identity.  They follow the existing shared-track ordering and
comparison visibility rules; folding neither suppresses a selected comparison
facet nor changes its source facts.

### Acceptance and compatibility

Tests cover the default byte-identical `own-row` case; group-header folding
with no point table cells and required labels; every predecessor eligibility
outcome; duplicate relation determinism; comparison variants; route endpoints;
annotation anchoring; overflow; and public HALCYON materialization.  The
automatic policy is additive.  No compatibility shim is introduced for invalid
`group-header` configurations because silently moving a point to another row
would misrepresent the View's declared presentation intent.

## Whole-architecture review

| Boundary | Decision | Excluded responsibility |
| --- | --- | --- |
| Project / Scheduler | Relation and schedule facts, including canonical relation identity | Fold policy and geometry |
| View / projection | Selected point policy, eligible fold target, diagnostics, stable instance identity | Coordinates, text measurement, route geometry |
| Layout | Header/row tracks, mark and label bounds, ports, rounded path commands, relation routes | Raw Project traversal and renderer syntax |
| Scene | One-to-one primitive projection of completed placements | Theme metric lookup, target choice, geometry calculation |
| SVG / Typst / TikZ | Serialization of typed primitives and completed paths | Fallback geometry or semantic interpretation |

The design introduces no Project mutation, no persisted renderer syntax, and no
new Scene-side layout decision.  It is therefore consistent with the current
surface-quality foundation and keeps future mark shapes or fold targets
extensible through typed View and Layout values rather than special-case Scene
branches.

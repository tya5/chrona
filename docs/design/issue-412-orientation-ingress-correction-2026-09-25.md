# Design Correction — Orientation Ingress and Completed Geometry (#412)

**Status:** proposed for architecture review.
**Amends:** `issues-410-412-411-typography-orientation-system-font-design-2026-09-25.md`.

## Decision

Issue #412 delivers finite 90-degree rotation of an already horizontally
shaped text block.  It does not deliver vertical writing, CJK vertical shaping,
glyph-orientation selection, automatic rotation, or arbitrary-angle text.

The correction makes the prior ownership decision implementable:

* View v0.18 selects `horizontal`, `rotate-cw`, or `rotate-ccw` only for an
  axis-label declaration and a table-header declaration.
* Layout turns that intent into the completed orientation, exact rotation
  angle, baseline pivot, and physical occupied rectangle.  All fit, alignment,
  collision, clipping, and overflow decisions use the completed rectangle.
* Scene v0.5 transports both the finite orientation and the Layout-selected
  `rotationDegrees`.  An adapter serializes that supplied transform about the
  supplied baseline and does not map an orientation to an angle itself.

`writingMode` is removed.  It did not control text writing and was therefore a
false product claim.  Layout Profile v0.8 has two truthful, independently
named declarations:

```yaml
flowDirection: horizontal
dependencyNetworkFlowDirection: horizontal # or vertical-rl / vertical-lr
```

`flowDirection` is the review-surface coordinate-flow declaration and v0.8
currently permits only `horizontal`.  `dependencyNetworkFlowDirection` is the
existing finite graph-axis choice and is the only location that permits the
two vertical directional values.  Neither value means text is vertical.  All
shipped profiles declare both explicitly; their current behavior maps to
`horizontal` for both.  There is no v0.7 reader.

## Versioned input contracts

### View v0.18

View v0.18 replaces v0.17 without a compatibility reader.  It introduces the
closed `textOrientation` enum:

```yaml
axis:
  tiers:
    - unit: month
      every: 1
      role: labels
      label:
        form: short-month
        align: start
        overflow: diagnose
        orientation: rotate-cw

tableColumns:
  - id: owner
    source: {field: owner}
    format: text
    missing: blank
    align: start
    width: content
    headerOrientation: horizontal
```

`label.orientation` is required whenever `label` is required, including every
concrete and automatic label form branch.  `headerOrientation` is required for
every table column.  Public Views state `horizontal` explicitly except the
designated corpus fixture.  Ordinary table cells intentionally have no
orientation field: this issue is a label/header capability, and a future
surface need must declare its own semantic ingress rather than smuggling a
general text transform through table facts.

Normalization produces:

```text
AxisLabelIntent(..., orientation)
TableColumnContent(..., header_orientation)
```

with no untyped schema maps beyond the resource boundary.

### Layout Profile v0.8

Layout Profile v0.8 replaces v0.7 atomically.  Its required root members are
`version`, `id`, `flowDirection`, `dependencyNetworkFlowDirection`,
`requiredThemeTokens`, and `reviewSurface`, alongside the existing standalone
or derived-profile alternative.  `LayoutManifest` has the corresponding typed
members.  The dependency-network solver receives only
`dependency_network_flow_direction`; review-surface composition receives only
`flow_direction`.  A vertical network direction may transpose node placement
and routes but cannot rotate its labels.

## Completed text geometry

`TextOrientation` is the same closed input/result vocabulary:

| Orientation | `rotationDegrees` in physical y-down coordinates | Occupied dimensions |
| --- | ---: | --- |
| `horizontal` | `0` | `(W, H)` |
| `rotate-cw` | `90` | `(H, W)` |
| `rotate-ccw` | `-90` | `(H, W)` |

For a measured horizontal block of painted width `W`, block height `H`, font
size `S`, and baseline pivot `(x, y)`, Layout starts from the local rectangle
`[0, W] × [-S, H-S]`.  It rotates all four corners about `(x, y)`, takes their
physical bounding box, and emits that exact `Rect` as the occupied bounds.
Thus clockwise rotation has local bounds `[S-H, S] × [0, W]`, while
counter-clockwise rotation has `[−S, H-S] × [−W, 0]`.  This is the canonical
calculation; no caller substitutes a simple width/height swap without anchor
translation.

Multiline text is first shaped and measured as one horizontal block with
`H = lineHeight × fontSize × lineCount`, then rotated as one block.  The
baseline remains the transform pivot for the first line.  The run's completed
records are:

```text
TextPlacement(
  bounds=<rotated physical Rect>, baseline=(x, y),
  orientation=<finite enum>, rotation_degrees=<0 | 90 | -90>,
  lines=<painted horizontal lines>, TextTreatment=<existing completed values>
)
```

Scene v0.5 `TextLayout` requires `orientation` and `rotation_degrees` and
validates the exact pairing.  Scene v0.4 remains a historical schema; the
serializer and generated public scenes move atomically to v0.5.  A malformed
or unpaired orientation/angle is a presentation-contract failure, rather than
a renderer default.

## Layout rules

### Axis labels

Axis label fit receives a completed measurement, not a width scalar.  Its
inline condition is `occupied_inline_size <= interval_inline_size`; the tier
lane condition is `occupied_block_size <= allocated_lane_block_size`.  Before
placing labels, Layout selects forms/thinning and allocates all label-tier
lanes within `timeline-axis` bounds.  A failure follows the declared
`diagnose` or `thin-with-record` policy; it does not spill into the timeline.
Alignment is performed against the completed inline extent.  The baseline is
then selected so the completed physical bounds lie in that lane.

### Table headers

Table-column allocation measures a header with its declared orientation and
measures cells horizontally.  A header contributes its **occupied inline**
extent to its column's natural minimum, so a rotated header cannot force a
horizontal-width allocation.  Layout separately computes the maximum
header-row **occupied block** extent and reserves it before row placement.
Header baseline/alignment is chosen within that reserved row from the completed
rectangle.  If the table slot cannot contain the reservation, it raises
`E_LAYOUT_TABLE_OVERFLOW`; a width failure retains the established declared
table overflow policy.  A rotated header may never overlap the first data row
or escape its table header region merely because its unrotated text fitted.

All non-axis/header text remains horizontal in #412.  The later #404 group
column invokes the same `place_text` orientation argument and uses this same
completed geometry, but #412 does not invent a group-column schema member.

## Projection contract

Every text-capable adapter consumes `TextLayout.rotation_degrees` and the
provided baseline pivot.

* SVG emits `transform="rotate(<degrees> <baseline-x> <baseline-y>)"` for a
  nonzero angle and no transform for zero.  SVG-derived PNG/PDF therefore
  inherit the exact source transform.
* Typst and TikZ receive the supplied degrees in their native text transform
  expression; neither backend examines `orientation` to choose a degree.
* Scene/SVG tests prove that no adapter computes an angle, measures text, or
  changes the occupied rectangle.

## Authority and migration

| Layer | Owns | Must not own |
| --- | --- | --- |
| View v0.18 | finite semantic orientation intent | coordinates, angle, measurement, adapter syntax |
| Profile v0.8 | truthful surface/network axis declarations | text orientation or text shaping |
| Layout | measurement, occupied bounds, baseline, angle, fit, lanes, overflow | backend transform syntax |
| Scene v0.5 | typed transport of completed text geometry | recomputation or fallback |
| Adapter | serialization of provided angle/pivot | angle inference, measurement, collision policy |

All Views, profiles, contract maps, schema inventories, parser/resource types,
tests, and public corpus resources migrate atomically.  Old versions are not
read.  The immutable Scene provenance records the exact hashes of View and
Layout resources, so a View/Profile contract migration necessarily changes the
generated Scene even before a visible rotated label is selected.  Scene v0.5
and the generated corpus therefore migrate in the same public release unit as
the View/Profile changes.  Within that unit, unchanged visible geometry remains
byte-stable; provenance, manifest-version, and required text-layout contract
fields are reviewed as intentional versioned changes.

## Acceptance criteria

1. v0.17 View and v0.7 profile declarations reject; all public resources use
   explicit v0.18/v0.8 values.
2. Unit tests prove each finite orientation's exact bounds and pivot, including
   multiline text.
3. Axis and header tests prove fitting, lane/header reservation, collision, and
   declared overflow use the rotated rectangle.
4. Scene v0.5 rejects invalid orientation/angle pairs and projection tests
   prove Scene retains Layout's exact bounds, baseline, and angle.
5. SVG, Typst, TikZ, PNG, and PDF evidence use the identical supplied angle;
   structural tests reject adapter-side angle mapping or text measurement.
6. A public corpus artifact intentionally contains rotation.  #404 can reuse
   the completed facility without adding a second transform pipeline.

## Correction — atomic publication boundary

Materializer verification on the v0.18/v0.8 ingress prototype established that
the previously planned independent I412-1 publication is not materializable:
the generated Scene's provenance changes whenever those immutable inputs
change, while a v0.4 Scene cannot represent the required completed text angle.
The implementation may retain internal checkpoints for contract migration,
geometry, and adapters, but their public publication boundary is one atomic
#412 release unit containing the Scene v0.5 and regenerated corpus evidence.
This is a dependency imposed by the reproducibility contract, not a relaxation
of the no-compatibility rule.

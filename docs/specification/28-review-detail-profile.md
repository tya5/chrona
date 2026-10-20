# Review Detail Profile v0.1

**Status:** Design complete — M23 input contract

## Ownership and boundary

A Review Detail Profile is a versioned presentation resource
(`chrona/review-detail-profile/v0.1`) consumed only after View selection and schedule
projection. It composes existing facts; it does not change Project, schedule, Actual
alignment, or summary metric semantics. Its structural authority is
`review-detail-profile-v0.1.schema.yaml`.

The complete M23 surface set has four members:

- `legend`: ordered semantic roles (including `planned`, `actual`, `variance`,
  `milestone`, `dependency`, and the bounded `progressFill` key below) with
  user-facing labels, owned by the Detail Profile;
- `groupDetails`: presentation-only label and bounded description keyed by the
  View-selected group ID;
- `milestones`: a View-selected ordered list of point object IDs; their title and
  scheduled date are derived from the existing projection;
- `observations`: a read-only, source-labelled table. Rows are literal presentation
  observations with stable IDs, cells, and an optional emphasis role. They must carry a
  `source` string and cannot be used by scheduler, Actual reconciliation, or summary
  metrics.

This keeps external supplier notes visibly attributable without fabricating Actual or
turning slide content into scheduling input.

## Style encoding legends (#419 S2)

Style-derived entries coexist with semantic Detail keys without replacing
their ownership. A scoped entry displays `title: value`; its authored title is
required and non-blank. Global Style entries display the domain value, prefixed
by an authored title when present. Stable identity uses Style/rule/scale,
canonical selector and value, never title or current match count. Preserve scale
domain order and the existing folded Other entry.

Source sizing may reserve potential entries. Layout filters them against final
visible placements and effective paint channels, then places only values
actually painted; explicit glyph colours and stroke-only parts do not create
encoded fill swatches. View encoding keys follow the same final-painted
occurrence closure described below: when every planned occurrence has an encoding key, the base
planned/forecast key is omitted; a mixed encoded and unencoded set retains the
base key.
An estimated-delta explanation may remain without a swatch under
[Spec06's forecast rule](06-view-model.md#85-explicit-forecast-presentation-1634).
It explains status, not ink, and contributes no swatch separability claim.
After selecting the final route/label option, recompose filtered Style entries
inside the conservatively allocated legend/footer slots. Final canvas completion
uses the filtered legend extent, not candidate-only growth; it does not restart
row, route or annotation layout.
All scale-derived finite keys use their completed category colour as key ink.
For a `rule-pair` key that colour is its stroke; width/opacity come from the
canonical scale-legend Theme role. This also corrects the older View key's
ignored colour override; it does not change the chart encoding's channel.
`showScope` opts into an extra qualifier, exactly `when ` plus canonical selector
JSON (all selector keys and compound predicates follow its canonical order).
No independent formatter or executable language is introduced. Allocate using
the primary label; append that qualifier only when it is measurable and fits the final
allocation. A qualifier-only failure omits it without rejecting the encoding or
its primary title/value. Canonical scope metadata remains beside the completed
Scene swatch whether or not that optional qualifier is visible.

## Realized semantic keys (#1679)

Semantic and scale-derived legend candidates are admitted from final completed
painted-occurrence witnesses, not from declarations or source availability
alone. Layout and the pure presentation model share the completed paint and
visibility closure; Scene and adapters project the resulting entries and do
not infer, select, or suppress keys. Actual-range keys use the realized
actual-trait/Style ink. A declared comparison with no available bound source
contributes no comparison key; a supplied source with blank values retains its
declared missing-value behavior.

Span Actual grouping identity is semantic meaning plus the set of effective emitted
ink colours, including opacity, admitted gradients and pattern treatment.
For a filled figure these are its visible fill inks; borders do not introduce
another meaning. Only a figure with no visible fill uses its stroke inks.
Multipart figures use all visible fill parts together, not one key per part.
Fill, stroke, outline, width, dash and glyph geometry are drawing variants,
not separate meanings. Equal-ink Actual occurrences coalesce across variance
classes in first-seen order; their first premeasured complete witness represents
the group even when an equivalent later occurrence supplies final visibility.
The full paint witness is retained for projection, not weakened to this grouping
identity. Distinct semantic families otherwise remain separate. Existing finite
key shapes remain deliberate ink projections, not copies of source geometry.

A multipart point glyph is one realized mark, not several independent
coloured marks. Its key preserves the ordered completed part paints and the
glyph geometry as one miniature figure with one label. Composite identity
retains the ordered effective paints and canonical glyph geometry/part
structure, excluding resource names, translations and placement bounds. Those
details select its representative miniature, not extra same-colour keys.
A declared finite circle or
rule-pair remains an intentional projection of the composite's first visible
part ink, rather than a separate key for every internal colour.

Layout reserves and completes the composite footprint and parts; the existing
point-swatch size override also applies to this glyph key. Coalesced candidates
reserve the largest required glyph footprint before measurement. Scene emits
the completed sibling Symbol parts under one figure identity and consumes
their completed paint witnesses. The ordinary whole-figure contrast rule
applies unchanged: an internal part is not tested as a standalone Rect against
canvas. No palette substitution, contrast exemption or corpus-specific branch
is introduced.

The authored Actual label is retained for one colour group. With multiple groups,
a group representing exactly one variance class uses only its own Ahead / On
track / Behind qualifier. An unclassified or shared-class group uses the base
label rather than asserting one class or listing several qualifiers. No colour
names or hashes are invented. View wording targets `actual-ahead`,
`actual-on-track`, and `actual-behind` override those qualifiers, not Theme roles.
The base `actual` wording still overrides the authored base label. These
derived targets exist when an Actual legend candidate is declared; an unused
valid override does not create a key.

A positive completed progress submark contributes a separate key using the
existing `progressFill` semantic. Its default label is `Progress`; a declared
Detail `progressFill` entry supplies label/order/shape instead, and
`wording.legend.progressFill` overrides the label. Without an explicit entry,
place it immediately after Actual, else after Planned/Forecast, else last.
Zero-width or absent submarks contribute none. A Progress key is redundant when
every visible progress submark has the same effective ink-colour set as its
completed host; omit it in that case. Compare each typed host identity, not the
union of unrelated Actual colours. These rules add no semantic
registry role or project-specific YAML repair.

Before measurement, candidate sizing reserves a superset of all potential
Actual paint groups and positive-progress keys, including distinct Style
paints; final filtering must not discover an unreserved key. After final
route/label selection, Layout recomposes the filtered entries once
inside the conservatively allocated legend/footer slots. Canvas completion
replaces candidate-only legend growth with the final caption-restored extent,
retaining the declared allocation minimum and all other completed geometry.
It does not retry route, row, or annotation layout.

### Realized point-state keys (#1847)

Point occurrences retain their distinct `planned`, `actual` and `forecast`
meanings. A key's grouping identity includes its declared legend owner, typed
state and complete canonical glyph/paint witness, for simple and multipart
glyphs alike. Equal signatures within one owner/state coalesce; different
states never coalesce merely because their ink matches. Span Actual's existing
ink/variance grouping and Progress semantics are unchanged.

A declared Detail entry matching an explicitly Style-selected point role owns
those points, ahead of the general `milestone` entry. Otherwise `milestone`
owns point states; when absent, the corresponding declared `planned`, `actual`
or `forecast` entry may own its state's points separately from range keys.
No declared owner means no synthesized point key. Ownership is explicit role
and occurrence data, never a title, project name or inferred profile value.
More-specific ownership prevents duplicate coverage by the generic entries.

Expand each owner at its authored position, preserving unrelated entry order,
with states ordered Planned, Actual, Forecast and variants in first-seen order.
A point-specific owner keeps its authored/wording label for one final state;
multiple final states append ` · ` and the localized `planned-plain`, `actual`
or `forecast` legend wording. A range-semantic owner's point keys append the
localized `milestone` wording to distinguish them from its range key. Repeated
variant labels remain subject to the existing duplicate-label diagnostic; do
not invent colour names or hashes. All potential qualified labels and maximum
glyph footprints are reserved before measurement; final visible point witnesses
alone admit keys and determine single-state labels, without rerunning layout.

Chart and key glyphs use the same selected-symbol and outline kernels, including
normalized shape traits and ordered part paints. Canonical identity excludes
resource names and placement translations/bounds. Scene/adapters receive
completed figures, not point-state inference. Explicit circle/rule-pair shapes
remain intentional projections and still participate in ambiguity checks.
Migration: the former combined milestone key and point/range Actual coalescing
are replaced by these state-aware keys; schemas and scheduling kinds do not change.

A View visual targeting a legend role binds to each completed label of that
role, including realized colour groups with stable hashed identities. Layout
passes this explicit role-to-label mapping to text-visual composition; Scene
does not infer aliases. An absent final role keeps the existing invalid-target
diagnostic and does not recreate a filtered key. Exact placement-ID selectors
retain their single-target contract.

## Default comparison keys and ambiguity diagnostics (#1703)

Snapshot and deadline marks contribute default semantic key candidates, using
the existing `snapshot` and `deadlineMark` roles and labels `Baseline` and
`Deadline`. Reserve candidates only when the selected projection can draw those
meanings. Final completed painted occurrences decide admission, as above;
source availability alone does not prove that a key is visible. This does not
create a legend slot in a Layout Profile that declares none.
That restriction concerns these comparison defaults; Spec50 separately defines
the intrinsic dependency-network critical key (#1727).

An explicit Detail legend entry for either role supplies its existing order,
label and finite-shape choice instead of a second default entry. Preserve the
relative order of authored entries. Append missing defaults in the order
Snapshot, Deadline, before scale-derived entries; the existing Forecast and
Progress insertion rules remain unchanged. View `wording.legend.snapshot` and
`wording.legend.deadlineMark` override the selected labels, including defaults,
without creating keys for absent final occurrences.

Detail body MAY declare `unkeyedLegendRoles`, a unique array whose closed values
are `snapshot` and `deadlineMark`. Omission is the empty array: neither default
is opted out. A listed role contributes no candidate. Declaring that same role
in `legend` is a contradictory policy and fails before Layout with
`E_DETAIL_LEGEND_POLICY` at the corresponding
`/body/unkeyedLegendRoles/<index>` pointer. This optional v0.1 addition does not
retype existing Detail fields. The owner-approved default-key correction may
change existing visible legends; it is not a byte-preservation promise.

After final filtering and recomposition, Layout emits
`W_LEGEND_LABEL_DUPLICATE` for different surviving key meanings with the same
displayed label, including text transformation, scope qualification and
ellipsis. It emits `W_LEGEND_SWATCH_COLLISION` when different meanings have the
same realized key figure. Both warnings identify the two meanings, roles and
completed key identities. Repeated witnesses of one coalesced meaning do not
warn, and filtered-away candidates participate in neither check.

All surviving semantic and encoded keys additionally use
[Spec 60 §5.1](60-declared-colour-scales.md#51-domain-separability-421)
for colour separability under normal vision and all three simulated deficiencies
(`W_LEGEND_COLOR_NOT_SEPARABLE` by default; a Scheme claim enforces that mode).
Exact whole-figure equality and perceptual
colour similarity are distinct findings; neither substitutes for the other.

Swatch comparison uses completed glyph/path geometry relative to its key box
and the effective emitted paint, not semantic IDs, placement translation,
resource names or a fill-only palette. Retain ordered multipart glyph parts,
finite shape distinctions, stroke/fill channels, opacity, width, dash,
admitted gradients/patterns and line terminals where drawn. Reuse the shared
paint resolvers and completed witnesses; do not introduce a second paint
interpretation. Equal figures remain faithful to the chart: diagnostics never
invent ink, change glyphs, coalesce different meanings, or repair project YAML.
Catalogue-pattern keys retain completed catalogue admission when selecting the
shared paint family and witness. Their tile primitives own intrinsic stroke
widths; comparison must not require an unused host-role `strokeWidth` or treat
the admitted substrate as an ordinary outline. Ordinary stroke validation stays
unchanged. This is the same paint contract used by Scene, not a diagnostic fallback.
Completed shape kind and channel selection also determine the shared paint family:
stroke-only shapes and paths use path paint; fill-only hosts use solid paint.
Do not infer a mark family that requires an unpainted fill for a completed edge path.

For composed point keys, Layout retains a canonical local completed geometry
witness from the same selected-symbol/outline kernels as the placed figure.
Compare that witness and the completed part paints, not a reconstruction from
translated floating-point contours. Preserve normalized shape traits and ordered
parts, including completed outlines; placement-dependent numerical noise must
not defeat translation/footprint invariance. This witness is internal to Layout;
Scene/SVG geometry and physical stroke paint are unchanged.

These are semantic diagnostics on the existing general Layout-to-Scene
diagnostic/provenance path, not fit fallbacks. Scene carries them unchanged;
adapters and render-warning collection do not infer legend meaning.

## Finite legend key shapes (#1562)

A `legend` entry MAY declare `swatchShape: circle|rule-pair`. Omission retains
the existing key, paint, sizing and identity. The shape does not change its
semantic role or optional period `sourceRef`.

`circle` draws a flat filled disk using the keyed Theme fill, or its stroke
ink when no fill exists, with the same opacity and existing scale-key fill
override. It uses the area `swatchBlockSize`, else the legacy side. `rule-pair`
draws two vertical strokes at one-quarter and three-quarters of the key box,
using the keyed stroke ink/width/dash/opacity. The shared ink witness preserves
that dash in both painted paths and the final legend signature; a deadline key
therefore matches its tick/run without a second style mechanism. A circle
remains a flat filled disk, without a borrowed dash. Existing inline/area sizing applies;
the box expands to at least three stroke widths inline and two blockwise.
The finite glyph replaces source pattern, terminal and effect geometry; it
does not invent a colour or duplicate a Theme palette. Missing required ink
or width uses the existing Theme diagnostics. The milestone key retains the
existing planned/gate paint-role selection; semantic aliases retain theirs.

Layout owns the footprint, measurement and completed contours/strokes. Scene
completes this typed ink-channel relation and clears transient intent before
serialization. Adapters receive ordinary painted Symbol/Path primitives and
perform no legend inference. Source-bound period keys with absent background
remain absent. Entries are measured individually, including repeated roles
with different source identities or shapes.

## Layout integration

The Review Detail Profile is the single contract for detail wording and rows. Its body
may contain `groupDetails`, `milestones`, and `observations`;
at least one is required.

Resolved Layout may allocate `legend`, `group-details`, `observations`, and
`milestones` slots. The solver allocates them from declared regions and emits their
rectangles; no coordinates are stored in a Detail resource. A declared profile panel
binds exactly one matching slot. Duplicate source slots diagnose. A required slot with
no available content diagnoses; preferred or optional absent content emits nothing.
The SVG adapter draws completed Scene primitives in stable logical order and retains
source metadata for every derived item.

Layout Profile v0.2 exposes the closed slot-source vocabulary used by detail sources.

## Resolution and validation

Group details are filtered against group IDs present in the selected Review Projection
and emitted in View group order. An unknown group ID yields
`E_DETAIL_GROUP_REFERENCE`. Each profile group ID is unique.

Milestone IDs preserve profile order and must resolve to selected Point objects in the
Review Projection. An unknown, unselected, or non-Point ID yields
`E_DETAIL_MILESTONE_REFERENCE`. Title and scheduled date are always derived from the
existing projection; the profile cannot restate them.

Observation column IDs and row IDs are unique. Every row contains exactly the declared
column keys, a stable ID, and a non-empty `source`. Missing provenance yields
`E_DETAIL_OBSERVATION_PROVENANCE`; a non-rectangular row yields
`E_DETAIL_OBSERVATION_CELLS`. `normal`, `attention`, and `critical` are closed
presentation emphasis values. They map to existing Theme paint roles `text`,
`variance-ahead`, and `variance-behind`; they do not express delivery status.
Cell typography remains the `text` role, independently of emphasis paint.
Column headers preserve declaration order and use table-header typography. Each
row visibly renders its exact source attribution before its cells; no invented
provenance label is added. Attribution is ordinary ground Text with purpose
`observation-source`, not a primary table cell or fabricated column. Headers and
cells have purposes `observation-column-label` and `observation-cell`, with the
existing header/text/emphasis paint roles. Header `sourceRef` retains the raw column
ID; attribution/cell `sourceRef` retains the raw row ID, and injectively escaped
placement IDs distinguish cells. They do not reference primary surface rows/columns.
Native column allocation uses measured minima and
equal flexible shares, with the existing table gutter and the slot's overflow
policy. Wrapped source/cell lines determine natural row height.

Panel geometry reuses Layout slots and Theme metric bindings rather than introducing
adapter constants. If content cannot fit its slot, the declared
slot overflow policy applies where its compact representation is feasible.
Required content that cannot fit completes at measured natural size with a
Layout warning and expanded canvas under Specification 33 Section 13; it does
not yield a fit refusal.

## Input and Scene boundary

The review command accepts one optional Review Detail Profile alongside Project,
Actual, View, Theme, and Layout. The profile is
validated before measurement. `SurfaceContentInput` carries normalized immutable
detail content; it carries no coordinates. Post-solve slot admission validates the
matching panels without reselecting those facts. Layout measures and places completed
panel primitives and attaches the profile entry ID or Project object ID as
`source_ref`; Scene projects that closure. Adapters MUST NOT read the profile or
recompute layout.

## M23 acceptance rules

1. A preset changes all labels, descriptions, legend order, milestones, and observation
   rows through resources, never preset/title/sample branches.
2. Unknown milestone IDs, unsupported legend roles, duplicate row IDs, overfull required
   slots, and missing observation provenance diagnose deterministically.
3. Plan/Actual bars, dates, and variance continue to originate only in the existing
   Review Projection.
4. The same Project/View/Style/Theme/Layout/Detail closure produces identical SVG.
5. Profile-independent renders remain byte-identical when no review-detail profile is
   supplied.
6. Conformance includes schema negatives, semantic-reference negatives, required
   overflow, source metadata, and a repeated-render byte comparison.

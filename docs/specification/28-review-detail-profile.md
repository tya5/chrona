# Review Detail Profile v0.1

**Status:** Design complete — M23 input contract

## Ownership and boundary

A Review Detail Profile is a versioned presentation resource
(`chrona/review-detail-profile/v0.1`) consumed only after View selection and schedule
projection. It composes existing facts; it does not change Project, schedule, Actual
alignment, or summary metric semantics. Its structural authority is
`review-detail-profile-v0.1.schema.yaml`.

The complete M23 surface set has four members:

- `legend`: ordered semantic roles (`planned`, `actual`, `variance`, `milestone`,
  `dependency`) with user-facing labels, owned by the Detail Profile;
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

## Style encoding legends (#419 S2; implementation pending)

Style-derived entries coexist with semantic Detail keys without replacing
their ownership. A scoped entry displays `title: value`; its authored title is
required and non-blank. Global Style entries display the domain value, prefixed
by an authored title when present. Stable identity uses Style/rule/scale,
canonical selector and value, never title or current match count. Preserve scale
domain order and the existing folded Other entry.

Source sizing may reserve potential entries. Layout filters them against final
visible placements and effective paint channels, then places only values
actually painted; explicit glyph colours and stroke-only parts do not create
encoded fill swatches. Existing View encoding legend policy is unchanged.
`showScope` opts into an extra qualifier, exactly `when ` plus canonical selector
JSON (all selector keys and compound predicates follow its canonical order).
No independent formatter or executable language is introduced. Allocate using
the primary label; append that qualifier only when it is measurable and fits the final
allocation. A qualifier-only failure omits it without rejecting the encoding or
its primary title/value. Canonical scope metadata remains beside the completed
Scene swatch whether or not that optional qualifier is visible.

## Finite legend key shapes (#1562)

A `legend` entry MAY declare `swatchShape: circle|rule-pair`. Omission retains
the existing key, paint, sizing and identity. The shape does not change its
semantic role or optional period `sourceRef`.

`circle` draws a flat filled disk using the keyed Theme fill, or its stroke
ink when no fill exists, with the same opacity and existing scale-key fill
override. It uses the area `swatchBlockSize`, else the legacy side. `rule-pair`
draws two vertical strokes at one-quarter and three-quarters of the key box,
using the keyed stroke ink/width/opacity. Existing inline/area sizing applies;
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

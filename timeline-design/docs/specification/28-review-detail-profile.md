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
  `dependency`) with user-facing labels, owned exclusively by the resolved v0.2
  Presentation Settings Detail;
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

## Layout integration

For the v0.2 path, `29-schema-owned-presentation-settings.md` and the `detail`
definition in `presentation-settings-v0.2.schema.json` are the single contract for
legend labels, templates and formatters. The Review Detail Profile MUST NOT contain a
parallel legend. Its body may contain `groupDetails`, `milestones`, and `observations`;
at least one is required.

Resolved Layout may allocate `legend`, `group-details`, `observations`, and
`milestones` slots. The solver allocates them from declared regions and emits their
rectangles; no coordinates are stored in a Detail resource. A declared profile panel
binds exactly one matching slot. Duplicate source slots diagnose. A required slot with
no available content diagnoses; preferred or optional absent content emits nothing.
The SVG adapter draws completed Scene primitives in stable logical order and retains
source metadata for every derived item.

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
presentation emphasis values. They map to existing Theme roles `body`,
`variance-ahead`, and `variance-behind`; they do not express delivery status.

Panel geometry reuses schema-owned settings rather than introducing adapter constants:
group details use `layout.notes` plus `group`/`notes` typography; observation tables use
`layout.cellPadding`, `layout.row`, `tableHeader`/`body` typography, and row-rule
strokes; milestone digests use `layout.summary`, `summaryHeader`/`summaryMetric`
typography, and Detail date formatting. If content cannot fit its slot, the declared
slot overflow policy applies. Required overflow yields `E_LAYOUT_REQUIRED_OVERFLOW`
with the source suffix.

## Input and Scene boundary

The review command accepts one optional Review Detail Profile alongside Project,
Actual, View, Style, Theme, Layout, and resolved Presentation Settings. The profile is
validated before Scene construction. `SurfaceContentInput` carries normalized immutable
detail content; it carries no coordinates. The Scene Builder measures and places all
panel primitives and attaches the profile entry ID or Project object ID as
`source_ref`. Adapters MUST NOT read the profile or recompute layout.

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

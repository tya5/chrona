# Design Amendment: Ungrouped Scene closure fields (#375)

**Status:** Accepted.

## Follow-up evidence

The first ungrouped-row correction enabled the next validation layer and
revealed two further representations of the same completed Layout fact:
`SceneGroup.id` is `""` for the ungrouped aggregate, and its group-decoration
primitive carries that same empty source reference.  These are not malformed
identifiers; they preserve a deliberate absence of grouping.

## Decision

Use the empty-permitted text schema for `SceneRow.groupId`, `SceneGroup.id`,
and primitive `sourceRef`.  Keep structural record identifiers (`row.id`,
`slot.id`, `primitive.id`, columns, resources) non-empty.  The schema thereby
distinguishes an empty completed grouping value from an absent/malformed record
without inventing sentinels or normalizing in consumers.

## Acceptance

An ungrouped corpus render validates with its group-decoration primitive, while
malformed structural identities remain rejected.

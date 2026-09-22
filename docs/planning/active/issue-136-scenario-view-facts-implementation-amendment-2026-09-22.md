# Issue 136 Scenario View Facts Implementation Amendment

This amendment is authoritative with the Scenario View Facts Design
Correction.  It repairs the incomplete S136-2 contract before the S136-3
HALCYON release gate proceeds.

## V136-1 — View fact contract and normalization

Update the View schema and typed resource contract to accept `{scenario: id}`
and `{scenario: title}` for table columns and summary metrics.  Normalize
table values from the table-subject item and normalize summary values from the
stable set of Scenario items actually used by the projection.  Pass only
already-resolved View facts into Layout.  Add focused schema, table, summary,
and non-Scenario missing-policy tests.

Acceptance: selected Scenario id/title are visible through declared View
sources; explicit multi-Scenario rows are deterministic; no Scenario logic is
introduced below content normalization.

## V136-2 — HALCYON release gate

Add a named Project Scenario, an automatic Scenario View/context, and a
materialized SVG plus closure evidence.  Add materializer tests for evidence
contents, deterministic regeneration, selected-Scenario identity change, and
absence of unselected Scenario provenance.  Review generated SVG differences,
run focused checks and the complete suite, then conduct the final architecture
boundary review and close Issue 136.

Each unit is a separate PR.  Before a merge, fetch `origin/main`, inspect the
commit range and PR state, require all CI checks, and merge serially.

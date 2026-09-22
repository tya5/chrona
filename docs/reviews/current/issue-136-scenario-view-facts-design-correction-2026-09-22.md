# Issue 136 Scenario View Facts Design Correction

## Trigger

The S136-3 release-gate review found that Project v0.5, View v0.7, the
resolver, and materializer provenance are present, but the declared Scenario
table and summary facts are not.  Current table and summary normalization has
no Scenario source.  Evidence alone does not satisfy the design requirement
that a rendered hypothesis can be named in View-owned content.

## Decision

View v0.7 adds the common source form `{scenario: id}` and
`{scenario: title}` to table columns and summary metrics.

For a table column, the value is derived from that row's table-subject item.
A Scenario item supplies its own stable scenario id and the title from the
primary Project declaration.  A primary, Actual, or Snapshot subject has no
Scenario value and follows the column's declared missing policy.  This makes
an explicit row containing several hypotheses unambiguous.

For a summary metric, the value is the stable-id-sorted, comma-separated list
of Scenario ids or titles actually referenced by the render.  The empty list
is an absent value, not an invented label.  Automatic mode therefore reports
its one selected Scenario; explicit mode reports precisely its named Scenario
sources.  The profile's normal missing/format policy remains authoritative.

The derived title lookup belongs to View content normalization.  Projection
carries only stable item/source identity; the Project remains the source of
Scenario declarations.  The resolver/application result continues to own
derived identities and materializer evidence.  Layout receives final text
runs, Scene projects completed placements, and the renderer serializes
primitives without Scenario-specific behavior.

## Acceptance

1. Schema and typed contracts accept only `id` and `title` Scenario source
   selectors in View table columns and summary metrics.
2. A table subject from a named Scenario resolves its id and declared title;
   a non-Scenario subject uses its declared missing policy.
3. Summary facts enumerate only Scenarios actually used by the projection in
   stable id order, including multiple explicit-row sources.
4. HALCYON's automatic Scenario context displays the selected title through a
   declared View source and its materializer evidence records the same
   Scenario id/title and derived identity.
5. No Scenario parsing, title lookup, placement rule, or geometry is added to
   Layout, Scene, or an SVG renderer.

## Architecture consistency review

The correction assigns author-visible hypothesis naming to the View content
boundary, where table cells and summary runs already become presentation
facts.  It keeps persistent declarations in Project Format, resolution and
provenance in the application boundary, schedule computation in Scheduler,
and all geometry downstream of finalized content.  The Project → View →
Layout → Scene → Renderer ownership model therefore remains intact.

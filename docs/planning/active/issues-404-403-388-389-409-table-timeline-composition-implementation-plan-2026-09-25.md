# Implementation Plan — Table--Timeline Composition (#404, #403, #388, #389, #409)

**Entry condition:** P1 design `7f8ccf58` and architecture review `bb619af6` are published; P2 failure-policy design/review `1b4431dd` / `5b52f0db` are published.

## I1. Contract migration

Update the live View schema, schema inventory, typed `ViewInput`/`TableColumn`,
resource parser, documentation, and all corpus Views atomically to v0.16.
Implement `table.hierarchyColumn`, finite column alignment/width, and finite
row decoration intent. Remove v0.15 acceptance/reader paths rather than
normalizing legacy data.

**Tests:** schema negative cases for each invalid hierarchy-column/width/
decoration combination; contract parser tests; inventory validation.

## I2. Hierarchy and measured allocation

Update projection and surface-content values to preserve automatic semantic
hierarchy versus explicit row nesting without WBS parsing. Replace positional
indentation and uniform `place_rows` allocation with per-row required extents,
`pack|fill`, and measured column allocation. Add placement invariants before
Scene construction.

**Tests:** hierarchy-column fixture with index-before-title, explicit-row tree,
content/FR/minmax allocation, mixed lane requirements, `pack`/`fill`, and
draft/immutable overflow policy branches.

## I3. Cross-slot decoration and completed background order

Add completed row/group decoration placements, finite background treatment and
background-only paint ordering. Project them through Scene and SVG/PNG without
builder ordering inference. Add completed-overlap validation.

**Tests:** one rectangle spanning table and timeline, alternating row/group
selection, rejected overlapping translucent fills, accepted outline calendar
closure, and adapter stable-order assertions.

## I4. Corpus, release, and acceptance

Migrate affected Themes/Layout Profiles/Contexts and add the specified corpus
slides. Regenerate only with the public materializer. Review generated SVG
differences as one batch.

**Acceptance:** focused tests for I1--I3, full pytest, schema/conformance and
structural gates, presentation coverage, every affected public materializer,
installed-wheel smoke, visual acceptance record, and three-platform CI. Push
each completed slice serially after fetching and comparing `origin/main`.

# Design Correction: Source observations in the presentation matrix (#390)

## Decision

The generated prior-art matrix has one typed column for Chrona and one typed
observation column for each named external source.  A source observation is
one of `documented`, `unknown`, or `not-applicable`.

`documented` means the named primary source explicitly documents the finite
capability category.  It is not a claim of semantic equivalence, visual
quality, or compatibility.  `unknown` means the review did not establish that
fact; it is the required value for every unresearched cell.  `not-applicable`
means the source's documented product scope makes the category inapplicable,
and requires an owner-local reason.

The Chrona column maps the closed #391 disposition into the reader-facing
values `supported`, `deferred`, or `deliberately-rejected`; owner, reason, and
responsible reference remain adjacent.  The generator owns the mapping, so
the typed registry remains the sole source of Chrona capability identity and
disposition.

## Source ownership

`tools/presentation_prior_art.py` owns a finite, checked-in observation table
keyed by capability identifier and source identifier.  It rejects a missing
capability, source, or observation.  Source identifiers and links are declared
once.  The output includes the link in each external-column heading and a
legend for observation values.

This table is research evidence only.  It is not imported by `src/chrona`,
does not expand the #391 ceiling, and cannot select a renderer behavior.

## Initial evidence boundary

The initial source set is Editorial Gantt, Mermaid Gantt, and Microsoft
Project Gantt formatting.  Only observations directly established by their
named primary documents may be `documented`; all other cells begin as
`unknown`.  This deliberately favors a complete, honest matrix over inference
from product reputation or adapter capabilities.

## Acceptance

* Every #391 capability row has one Chrona value and one observation for every
  declared external source.
* A missing/stale row, source, or observation fails a focused test.
* The generated Markdown puts each primary source in a column heading and
  explains `documented`, `unknown`, and `not-applicable`.
* The generator has no runtime imports other than the typed ceiling registry.

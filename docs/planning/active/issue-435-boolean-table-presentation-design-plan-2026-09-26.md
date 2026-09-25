# Issue #435 boolean table presentation design plan

## Objective

Replace accidental Python boolean stringification in table cells with an
author-declared, finite presentation contract.  A boolean fact must never
silently acquire reader-facing wording in the rendering pipeline.

## Confirmed starting point

`view-v0.19` permits `comparisonFacet: missingActual` with an absent format.
`ViewInput` normalizes that absence to `"text"`; `display_value` then reaches
`str(bool)`.  The three HALCYON gallery contexts reuse
`views/01-mission-brief.yaml`, so one View migration repairs all three
artifacts.  Scene and renderers only receive already rendered cell text and
must not receive a boolean-specific branch.

## Design questions and required decisions

1. Define a finite author syntax whose true and false output are both
   explicit, including a meaningful empty-string representation when desired.
2. Define the typed normalized value crossing from View ingress into review
   content, without retaining raw schema maps in Layout or Scene.
3. Reject the known boolean `missingActual` source without that value at View
   ingress; reject dynamically resolved boolean field values before
   presentation normalization as well.
4. Select readable HALCYON wording and prove no committed Scene contains the
   Python literals.
5. Review the design against the presentation boundary: View owns author
   intent, review-content owns fact-to-string normalization, Layout owns
   measurement, and Scene/adapters only project completed text.

## Non-goals

This slice does not create a general table-cell icon grammar, alter semantic
paint selection, or solve the contrast policy tracked by #431.  It may use
plain declared strings only; any icon treatment remains an independent use of
the established visual capability path.

## Completion evidence

The follow-on implementation plan must name the View schema/version transition,
typed contract, normalization tests, HALCYON migration, public materializer
regeneration, realization-report reachability check, and focused/full release
gates.

# Issue 308 Progress Fill Design Review

## Scope reconciliation

The Issue's original in-bar-label claim is complete through #310.  Its
object-state paint claim is complete through #314, using declared scales rather
than the removed rule engine.  The remaining issue scope is the progress fill
defined in Specification 61.

## Architecture review

Project and Actual resources remain the authority for fractions.  View selects
one source without defining data or geometry.  Layout transforms a selected
fraction and completed host bounds into a completed optional submark.  Scene
maps that placement to a standard primitive and Theme role; adapters serialize.
This direction prevents a renderer from choosing a fraction or inventing an
inset rectangle, and prevents a progress observation from becoming a schedule
input.

The source-specific host rule avoids falsely displaying an Actual fraction on a
planned bar.  It also makes absence explicit by omission, not by a fabricated
zero or a fallback estimate.  A separate `progressFill` semantic binding keeps
Scheme/Theme paint independent from both host facet and #314 scales.

## Rejected alternatives

* An unordered list of bar layers or a generic nested-rect payload would make
  Scene geometry authorable and create an unbounded renderer contract.
* Applying observed progress to a planned mark would conflate planned temporal
  geometry with Actual state.
* Extending colour scales to progress would treat a fraction as a category and
  reopen data-dependent paint policy.

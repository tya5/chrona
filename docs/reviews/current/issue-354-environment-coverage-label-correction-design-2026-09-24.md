# Issue #354 — Environment Equality and Coverage Label Correction

**Decision:** Accepted correction to the gallery collection contract.

## Trigger

The re-review correctly identified that the repaired surface pair still used
different viewport sizes.  A viewport changes the completed composition and
cannot be an undisclosed difference in a Design Space comparison.  It also
identified that #355's intentionally semantic schema backlog was presented by
the gallery as though it chose the next presentation set.

## Comparison environment contract

Every peer in a gallery set must have byte-identical declared `environment`.
This covers viewport, locale, font metrics, precision, and any later typed
environment field without introducing a parallel allow-list.  It is a shared
materialization condition, not a Design Space owner and cannot be added to
`supports`.  A mismatch raises `E_DESIGN_GALLERY_ENVIRONMENT_MISMATCH:<set>`.

`halcyon-two-surfaces` therefore uses the programme-board viewport (1920 ×
1080) in its dependency-network Context.  It must regenerate its committed
SVG and pass public materialization.  If the network cannot fit at that fixed
environment, the set returns to deferred rather than admitting a viewport
support escape hatch.

The existing semantic equality contract for Project and Actual remains
unchanged.  Target capability declarations are output requirements, not an
environmental presentation input; this correction deliberately does not make
different target capability subsets a false Design Space axis.

## Coverage label

#355's report owns semantic corpus coverage over Project, Actual Set, Snapshot
Reference, and Profile Package schemas.  It does not measure View, Layout, or
Theme vocabulary and must not be described as a gallery-set selector.  The
generated gallery index therefore labels and links it as **Semantic corpus
coverage**, explaining that it is only one curation input.  A future gallery
expansion may design a separate presentation-evidence inventory; it must not
silently widen #355's bounded schema scope.

## Architecture review

Environment equality belongs to the documentation validator because it checks
the declared Context evidence boundary.  It adds no resolver, Layout, Scene,
or materializer behavior.  Keeping semantic coverage narrowly named preserves
the distinction between corpus-contract evidence and presentation-gallery
evidence, retaining the established downstream-only documentation flow.

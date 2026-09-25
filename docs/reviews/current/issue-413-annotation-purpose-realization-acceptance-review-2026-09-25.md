# Issue #413 — Annotation Purpose Realization Acceptance Review

**Status:** accepted.
**Implementation:** `4b157f95`, `145d44ca`
**CI:** [run 36125813453](https://github.com/tya5/chrona/actions/runs/36125813453)

## Accepted boundary

The review surface now closes each declared annotation purpose into a typed
Layout placement with independently themeable box, text, and, where required,
leader semantics.  The View owns the common failure-policy ladder; Layout
selects its measured result and completes route and marker geometry; Scene
projects only the supplied placement identity.

| Requirement | Evidence | Result |
| --- | --- | --- |
| Purpose reaches distinct visual semantics | `AnnotationIntent` and `AnnotationPresentation` carry finite callout, highlight, note, and explanatory-arrow identities through completed text, shape, and relation placements. | Pass |
| Box, text, and leader are independently themeable | The semantic registry and Controller Z Theme declare separate purpose-specific roles; the corpus Scene has distinct box/text/leader visual roles. | Pass |
| Explanatory arrows have completed terminal geometry | Layout resolves `annotation-arrow-terminal` into `RelationPlacement.marker_end`; Scene and SVG project it without spelling an arrow marker. | Pass |
| Routing policy is isolated from dependencies | Layout Profile v0.7 supplies `annotationRouting`; dependency routes continue to consume only `relationRouting`. | Pass |
| Purpose does not alter fallback authority | Every typed intent carries the View-normalized ladder; Layout applies rail, side, or suppression consistently for all four purposes. | Pass |
| Public evidence realizes the declared vocabulary | Controller Z's annotations slide contains every purpose; the checked semantic realization report records four purpose-specific annotation-box roles as realized. | Pass |
| Scene remains projection-only | Structural tests reject annotation-purpose mapping and generic annotation semantic reconstruction in Scene; it consumes completed placement identities and marker geometry. | Pass |

## Verification

* focused typed-content, Layout, Scene, route-quality, realization-report, and
  public annotation-materializer tests passed;
* all declared corpus materializers reproduced committed bytes after the shared
  Controller Z Theme provenance update; generated Scene/SVG output was reviewed,
  including distinct box treatments, omitted highlight leader, and arrow marker;
* `python conformance/run_conformance.py` passed, as did generated-report and
  diagnostic-inventory freshness checks;
* a built wheel passed the size gate and isolated installed-wheel smoke test;
* CI run 36125813453 passed on Ubuntu, macOS, and Windows, including
  conformance, structural gates, report checks, parallel full pytest, wheel
  build, and installed-wheel smoke.

## Architecture review

The implementation retains the Project/View -> normalization -> Layout ->
Scene -> adapter authority chain.  Normalization is the only schema-map
boundary; Layout owns measured box selection, common fallback application,
orthogonal leader routing, and terminal geometry.  `AnnotationPresentation`
is carried as placement provenance, so Scene neither selects a purpose nor
reconstructs a semantic identity from an annotation ID or primitive prefix.
The generic annotation rendering fallback has been removed from this review
surface rather than retained as a parallel compatibility path.

## Disposition

Issue #413 is complete.  Its public evidence removes the annotation-purpose
gap previously recorded by #414; #414 remains responsible for the programme's
final release evidence disposition.

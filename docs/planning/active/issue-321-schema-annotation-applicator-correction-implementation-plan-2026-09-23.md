# #321 Schema Annotation Applicator Correction Implementation Plan

**Authority:** Specification 56 and the applicator-correction architecture review.

1. Make annotation traversal recurse through every `allOf` child while
   preserving the pure-`$ref` exemption.  Require examples for `allOf` wrappers
   with local assertions and add focused negative fixtures for nested
   conditionals and constrained references.
2. Annotate every newly reachable live branch with concise author language and
   context-valid examples.  Do not change schema acceptance semantics.
3. Run annotation and reference gates, conformance, structural checks, full
   parallel pytest, all public materializers, generated-SVG comparison, wheel,
   and isolated installed-wheel smoke.  Publish a replacement acceptance
   review, record the correction on #321, and close it only after every gate
   succeeds.

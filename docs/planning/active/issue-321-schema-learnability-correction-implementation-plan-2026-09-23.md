# #321 Completion Correction Implementation Plan

**Authority:** Specification 56 and the completion correction review.

1. Extend `SchemaViolation` and `explain_errors` with explicit ingress context;
   migrate Core and presentation contracts with focused identity tests.
2. Inventory every remaining schema ingress (operational resources, commands,
   guided authoring) and route it through the reducer without changing success
   values or public error IDs. Add focused bad-document tests.
3. Expand annotation traversal and example policy to applicators, patterns,
   formats, and local assertions. Add negative lint fixtures, annotate the live
   corpus, and validate all examples.
4. Run conformance, structural checks, full pytest, materializer byte checks,
   empty generated-SVG diff, wheel, isolated smoke, and publish a replacement
   acceptance review before reclosing #321.

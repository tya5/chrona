# Design Plan — Presentation Diagnostic Aggregation (#450)

## Objective

Make one invalid Draft render report every independent presentation-resource
schema and semantic violation in deterministic order, rather than failing at
the first `SchemaContractError` raised by resource loading.

## Confirmed current boundaries

- `schema_diagnostics.explain_errors` selects one violation from one validator
  iterator; this is the within-resource loss point.
- draft and immutable closure loaders convert that exception directly into one
  `ClosureError`; resource resolution therefore stops at the first bad input.
- `RenderRejected` already transports a list of Core diagnostics, while
  `RenderFailed` transports one presentation failure.  Aggregation must not
  make Layout/render run on malformed contracts.

## Design questions

1. Define an immutable ordered presentation-diagnostic value that retains
   resource kind/identity, RFC6901 pointer, rule, message, and phase.
2. Separate independent schema/contract collection from semantic checks that
   require a schema-accepted resource; dependent checks must be explicitly
   skipped, never guessed.
3. Define the render/CLI transport so a single-error report remains stable
   while a multi-error input returns all independently knowable errors.
4. Review all closure paths (Draft files, immutable references, preset and
   guided workspace normalization) to avoid creating a second validator.

## Required evidence

- a three-error View/Theme fixture reports all three in stable order;
- independent resources are all checked while malformed resources prevent
  dependent semantic work only;
- single-error wording/identity remains unchanged where it is public;
- focused closure/CLI tests and public materializer regression evidence.

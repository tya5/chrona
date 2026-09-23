# Design Plan: Schema Learnability and Diagnostic Explanations (#321)

## Verified starting point

The schema inventory declares 21 live author-facing schemas.  The repository
also contains the inventory schema and one example schema, for 23 YAML files
under `schemas/`.  Only two author-facing `description` keywords and no
`examples` keywords currently exist.  The current resource-contract validator
does preserve a deterministic RFC 6901 pointer in `SchemaContractError`; #255
now has nested View, Theme, and Layout regression coverage for that behavior.
It does not retain the JSON Schema keyword, expected values, or a
human-directed explanation.  Core Project validation emits raw jsonschema
messages and paths independently of the presentation-contract boundary.

The live Project v0.5 schedule union has four shapes.  `fixedPoint` and
`fixedSpan` both use `mode: fixed`, so an author and a validator must infer the
branch from the presence of `at` versus `start`/`end`.  Other unions include
both genuinely tagged shapes and key-shape/value unions that cannot honestly be
given a synthetic discriminator.  Normative specification documents currently
contain historical contract literals that do not correspond to a live schema;
no automated check distinguishes historical examples from current authoring
contracts.

## Design questions

1. Define what constitutes an author-facing schema node and the minimum
   description/example metadata required for editor hover, completion, generated
   reference, and diagnostics without narrating internal JSON Schema mechanics.
2. Define one structured validation-failure representation that preserves
   resource identity, RFC 6901 instance pointer, keyword, expected set/range,
   actual value category where safe, and a stable author-facing message.
3. Decide how union errors select one actionable failure without concealing
   valid alternatives.  Tagged unions must name their tags; key-shape unions
   must state the required forms rather than pretending they have a tag.
4. Define the clean Project schedule successor that replaces the ambiguous
   `mode: fixed` pair, its migration of first-party fixtures/resources, and the
   semantic invariants that prove no schedule meaning has changed.
5. Define an executable documentation-reference gate that distinguishes live
   normative contract declarations from explicitly historical material and
   derives its supported identifiers from schemas rather than a second list.

## Architectural constraints

* Schema documentation and diagnostics are ingress concerns.  They must not
  introduce parser fallbacks, schema recovery, renderer choices, or duplicate
  validation inside View, Layout, Scene, or adapters.
* Every user-visible pointer is an RFC 6901 pointer to the instance value, not
  a schema location.  Resource identity is retained independently of the
  pointer.
* A diagnostic explanation is deterministic for equal input/schema versions.
  It may summarize expected values but must not leak host paths, Python object
  representations, or nondeterministic validator ordering.
* The Project schedule successor is a contract migration, not a compatibility
  alias.  First-party authored resources, schemas, fixtures, docs, and public
  commands must move together; the old ambiguous shape must not remain an
  accepted hidden branch.
* Documentation checking recognizes archival/historical specification material
  explicitly.  It must not rewrite history or force old-version examples to
  validate as current resources.

## Required design outputs

1. A normative schema annotation profile: author-facing nodes, required
   `description`, selective `examples`, writing rules, and a mechanical lint.
2. A diagnostic contract and error-selection algorithm shared by Core Project
   and presentation resource validation, including enum, const, required,
   additional-property, type, range/pattern, and union cases.
3. A discriminated-union policy, a Project v0.6 schedule design, and an
   inventory of unions that remain key-shape or conditional by design.
4. A live-reference policy and documentation gate design, with a clear source
   of truth and migration treatment for obsolete prose examples.
5. An architecture review against the Core -> closure -> View -> Layout ->
   Scene -> renderer direction, plus UC/CLI authoring evidence.

## Planned implementation slices

The implementation plan may be published only after the preceding design and
review decide the exact contracts.  It must keep these reviewable boundaries:

1. Introduce the shared structured validation-explanation boundary and its
   focused contract tests; migrate resource and Core callers without changing
   accepted schemas.
2. Add annotation lint and annotate the live author-facing schemas in coherent
   resource-family batches, with representative examples and generated
   reference evidence.
3. Introduce Project v0.6's discriminated schedule contract and migrate all
   first-party Project resources, fixtures, CLI/conformance evidence, and
   semantic scheduling tests atomically.
4. Add the normative-document reference gate, correct live prose drift, and
   prove archived references are intentionally excluded.
5. Run full validation, public materializers, generated-output review, and
   regression checks.  A failed migration or a newly ambiguous union returns to
   design rather than being masked with compatibility parsing.

## Completion evidence

The completed design must specify the vocabulary and test matrix before any
schema mutation.  The completed implementation must prove: every live
author-facing schema passes annotation lint; representative bad documents emit
one stable path/expectation explanation; Project schedule branches are
unambiguous; live normative references resolve; historical prose is marked or
excluded deliberately; public materialization remains unchanged for migrated
semantic inputs; and the full suite succeeds.

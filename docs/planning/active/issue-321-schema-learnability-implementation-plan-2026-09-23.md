# Implementation Plan: Schema Learnability and Diagnostic Explanations (#321)

**Design authority:** [56 Schema Authoring and Diagnostics](../../specification/56-schema-authoring-and-diagnostics.md)
and its [architecture review](../../reviews/current/issue-321-schema-learnability-architecture-review-2026-09-23.md).

## I321-1 — Shared structural explanation seam

**Files:** add `src/chrona/schema_diagnostics.py`; update
`src/chrona/presentation/contracts/resources.py`, `src/chrona/core/validation.py`,
and the CLI error adapter only as required; add focused unit/CLI tests.

**Work:** Define the immutable internal violation value and deterministic
jsonschema-error reduction. Support the reviewed enum, const, required,
additional-property, type, range, pattern, tagged-union, and key-shape-union
messages. Preserve existing error IDs and RFC 6901 pointers; only enrich the
author-facing message. Route both Core and resource contract validators through
this seam without allowing the helper into successful typed projection.

**Acceptance:** malformed nested Project, View, Theme, and Layout inputs each
return one stable pointer/explanation; unknown properties include a deterministic
near-name only when appropriate; schema errors do not alter valid closures,
scheduling, Scene, or output. Focused tests and the complete suite pass.

## I321-2 — Live schema annotation profile

**Files:** add `tools/schema_annotations.py` and its tests; update every `live`
entry under `schemas/` named by `schemas/schema-inventory-v0.1.yaml`; update
conformance/workflow invocation and generated/reference evidence as needed.

**Work:** Implement the inventory-driven reachable-node traversal and annotation
lint. Add concise descriptions to all author-facing nodes and examples to
branches, unusual shapes, dates/durations, references, and other non-obvious
forms. Validate each example in its enclosing schema context. Annotate by owner
family in review, but publish the lint and complete live corpus together so no
live schema is exempted by an allowlist.

**Acceptance:** lint identifies a deliberately missing description/example with
a schema-location pointer; all live schemas pass; examples validate; annotation
metadata changes neither accepted instance semantics nor generated public SVG
bytes. Focused lint/schema tests and the complete suite pass.

## I321-3 — Project v0.6 discriminated schedule migration

**Files:** replace `schemas/project-v0.5.schema.yaml` with
`schemas/project-v0.6.schema.yaml`; update the schema inventory, package resource
tests, `src/chrona/core/validation.py`, `src/chrona/scheduling/scheduler.py`,
`src/chrona/presentation/contracts/resources.py`,
`src/chrona/presentation/model/authoring.py`, profile requirements, all Project
fixtures/conformance files/examples/tests/wheel smoke input, and normative current
documentation references.

**Work:** Introduce only `fixed-point` and `fixed-span` as the fixed schedule
tags; migrate every first-party point/span source accordingly and remove v0.5
from the live parser/inventory/package. Change scheduler checks to operate on
the fixed-tag set while retaining one fixed-placement implementation. Migrate
profile format constraints and public command evidence in the same commit.

**Acceptance:** valid v0.6 point/span/scheduled/rollup resources retain their
previous completed dates, dependency endpoint behavior, analysis, and public
CLI JSON content; v0.5 is rejected; no first-party `mode: fixed` or
`timeline/v0.5` remains outside explicitly marked historical material. Run
focused Core/scheduler/closure/CLI tests, materializer checks, generated SVG
diff review, complete suite, and installed-wheel smoke test.

## I321-4 — Normative contract-reference gate

**Files:** add `tools/validate_schema_references.py` and tests; update
`schemas/schema-inventory-v0.1.yaml`/schema inventory helpers if identifiers
must be exposed; annotate/correct `docs/specification/` occurrences and
`schemas/README.md`; wire the gate into conformance.

**Work:** Derive the current identifiers from live inventory entries and their
schema `$id`/version constraints. Parse explicit current/historical markers in
normative documentation, reject unclassified authoring declarations and stale
current identifiers, and exclude only `docs/archive` by path. Correct prose
that presents removed contracts as live; retain historical examples only with
their successor/archival label.

**Acceptance:** fixtures cover live success, stale-current failure,
historical-labelled success, and unclassified failure. All current
specification examples resolve to a live schema; historical documents remain
readable without being declared authorable. Focused gate tests and the complete
suite pass.

## I321-5 — Final integration and publication gate

Run the complete parallel pytest suite, schema inventory, annotation lint,
documentation-reference gate, conformance, public materializers, generated SVG
diff, wheel construction, and installed-wheel smoke test. Review diagnostics
for deterministic author wording and review schema/docs diffs for owner-boundary
accuracy. Publish the acceptance review only after all gates pass; then close
#321 with links to each implementation slice.

## Stop conditions

If an annotation needs to describe a policy not owned by its schema, if shared
diagnostics require downstream raw-document access, if a v0.5 compatibility
branch appears necessary, or if a documentation marker becomes a second contract
registry, stop implementation and amend the design/review before proceeding.

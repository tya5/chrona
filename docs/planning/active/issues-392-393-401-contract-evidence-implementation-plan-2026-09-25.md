# Implementation Plan: contract evidence and registry integrity (#392, #393, #401)

## Preconditions

This plan implements the decisions in
`docs/design/issues-392-393-401-contract-evidence-design-2026-09-25.md`.

## A1 — Schema-derived coverage (#392)

**Files:** `tools/presentation_coverage.py`, its focused tests/fixtures, and
the generated `docs/gallery/presentation-coverage.md`.

1. Make schema traversal collect finite values nested in maps, unions and
   conditional branches without a Theme-specific traversal rule.
2. Preserve stable path notation and distinguish wildcard map/array traversal.
3. Add a fixture where a newly introduced nested enum is reported without
   changing collector code.
4. Regenerate the report and confirm every marker/symbol shape is either
   realized or explicitly listed unrealized.

**Acceptance:** the report exposes nested Theme values and the focused test
proves a generic nested enum is discovered.

## A2 — Semantic binding integrity (#393)

**Files:** Scene annotation projection, semantic-registry structural test/tool,
focused Scene and registry tests.

1. Resolve annotation text by `annotationText`.
2. Add an AST/source-level binding-lookup audit over production Layout and
   Scene modules, excluding declarations and test files.
3. Assert all registry bindings are reachable, including `iconMark`; assert
   annotation text emits purpose `annotation-text`.

**Acceptance:** a deliberately unused fixture binding fails the audit, and no
annotation text primitive carries purpose `annotation`.

## A3 — Locale closure evidence (#401)

**Files:** Render Context/CLI contract tests, CLI help and relevant guide only
if evidence reveals a divergence.

1. Verify v0.15 schema, parser ingress and formatter rejection agree on the
   exact pair.
2. Add missing focused tests rather than changing historical schema versions.
3. Record the evidence in acceptance review; close #401 if all public ingress
   surfaces agree.

**Acceptance:** `en-US` and `ja-JP` pass; `en-GB` fails at public contract
validation or deterministic normalization; help/documentation state the pair.

## Program gate

Run focused tests, schema conformance, generated-report check, full `pytest`,
public materializer byte checks, generated SVG diff, wheel smoke, and the
three-platform CI workflow.  Publish source, generated evidence, and review
before closing #392, #393, and #401.

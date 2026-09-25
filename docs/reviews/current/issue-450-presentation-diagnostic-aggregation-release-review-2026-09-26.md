# Release Review — Presentation Diagnostic Aggregation (#450)

## Acceptance evidence

Issue source: https://github.com/tya5/chrona/issues/450, observed 2026-09-26.

| Literal acceptance criterion | Disposition | Evidence |
| --- | --- | --- |
| The three-error example above reports three diagnostics, each with its resource and pointer, in one run. | met | `test_cli_draft_schema_diagnostics_report_all_known_resources_with_provenance` constructs the stated two invalid View fields and one invalid Theme field, then asserts the three ordered `(code, resourceKind, resourceIdentity, sourceRef)` records in the one `chrona render` result. |
| The order is stable across runs and platforms. | met | `test_explain_all_errors_keeps_every_leaf_in_stable_pointer_order` and the CLI fixture assert deterministic order.  GitHub Actions run `36181548118` passed the conformance and pytest jobs on Ubuntu, macOS, and Windows. |
| A single-error input produces the same diagnostic as today. | met | Legacy `explain_errors` remains the singleton selection API; `test_explain_all_errors_flattens_union_wrappers_without_changing_legacy_explanation` and `test_cli_draft_schema_diagnostic_keeps_the_author_facing_explanation` protect the established pointer and author-facing message. |

## Additional release evidence

- `collect_presentation_contracts` separates resource-local schema explanation
  from ingress-wide collection, then runs dependent semantic checks only after
  the resource's schema acceptance.  Its focused contract tests cover all
  independent schema diagnostics and semantic ordering.
- Explicit Draft and indirect immutable Context ingress transport completed
  diagnostics without moving validation into Layout, Scene, or renderers.
  Structural inspection confirms the collector has no imports from those
  layers.
- Focused regression selection: 94 passed, 1 deselected.
- Public materializer characterization: 26 passed.  The regenerated SVG
  comparison is empty, so valid public materializations did not change.
- GitHub Actions `36181548118` passed public materializer reproduction and
  the full conformance/pytest/wheel matrix on Ubuntu, macOS, and Windows.

## Architecture conclusion

Diagnostic aggregation is an ingress concern.  `schema_diagnostics` owns
stable explanation of validator findings; the contracts collector owns
resource-wide accumulation and provenance; Draft/Context ingress owns
transport to author-facing diagnostics.  Layout, Scene, and serializers retain
their existing responsibilities.  The issue is accepted.

# Gallery freshness and viewport survey review

<!-- chrona:literal-acceptance/v1 -->

Design, architecture and implementation plan: [living record](https://github.com/tya5/chrona/issues/1474#issuecomment-6158249825).
Ready baseline: ac4ac88360708de5421baccf043f9e65c22f5e01. Tool repair:
d0108cd4, after the independently published gallery, Context ingress, annotation
fallback and Windows launcher fixes in PR1483/1484.
[Reviewer disposition](https://github.com/tya5/chrona/issues/1474#issuecomment-6167307115):
keep all capacity cases with exact expected diagnostic outcomes; defer core
allocation changes to #1490. API and CLI each accept all138 cases:117 render,
21 give their recorded refusal,0 unexpected outcomes. Gallery --check passes.
Focused tool tests15PASS; review/ledger tests7PASS. No product, examples or
generated-output changes in this remaining slice. Main adoption, current-head
PR gates and an exact-main containing-review three-OS release remain required
before closure; local passes alone are not release acceptance.
Architecture: expectations belong to the validation tool, not Layout policy.
API and CLI share the existing failure reporter's complete diagnostic payload
and exit code; no synthetic domain code or project-specific core exception.

## Literal issue acceptance

### Issue #1474

- Source: [issue](https://github.com/tya5/chrona/issues/1474)
- Observed: 2026-10-14

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | Both tools pass on main. | not met | Candidate API and CLI --jobs4 each pass all138 cases (117 rendered,21 exact expected refusals,0 failures); gallery --check passes. [Recorded outcomes](../../../tools/draft_viewport_expected_refusals.yaml) retain every case and link each group to #1490. [Tests](../../../tests/unit/tools/test_check_draft_viewport_matrix.py) reject changed code/message/source/component/exit, unexpected rendering, unlisted failures and missing cases. Final ready-main verification and release are pending. | — |
| 2 | Each is either in the CI gate or explicitly documented as manual. | met | Gallery remains in [conformance registration](../../../conformance/run_conformance.py). [CONTRIBUTING](../../../CONTRIBUTING.md) and the [tool docstring](../../../tools/check_draft_viewport_matrix.py) explicitly require the manual matrix when changing Layout allocation; no additional CI shard or duplicated whole-corpus PR run. | — |
| 3 | Do not edit `examples/**`. | met | [Source diff](https://github.com/tya5/chrona/compare/1299e952a22d855f81d04f32b5ad81ff0f462da8...0fa35d73) changes tools, synthetic tests, Layout fallback propagation and three renderer-owned documentation pages only. [Identity tests](../../../tests/unit/tools/test_check_draft_viewport_matrix.py) preserve authored bytes/snapshot/assets; derivative Contexts are temporary and truthfully pinned. | — |

## Programme-level criteria (optional)

None. Keep issue1474 open until the ready-main evidence and release gate complete.

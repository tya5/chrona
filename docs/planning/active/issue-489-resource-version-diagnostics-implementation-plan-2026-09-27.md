# Implementation Plan — Actionable Unsupported Resource Versions (#489)

**Published design base:** `229e6b99` on `main`. **Design chain:** [design plan](issue-489-resource-version-diagnostics-design-plan-2026-09-27.md), [design](../../design/issue-489-resource-version-diagnostics-design-2026-09-27.md), [architecture review](../../reviews/current/issue-489-resource-version-diagnostics-architecture-review-2026-09-27.md), and [Specification 56 §3.1](../../specification/56-schema-authoring-and-diagnostics.md). Do not start product code until this plan is public.

## Literal acceptance and publication units

| # | Literal issue acceptance criterion | Implementation evidence |
| ---: | --- | --- |
| 1 | Rendering a preset copy with an older View version fails with a code and message that name the found and supported versions, with `sourceRef: /version`. | End-to-end public CLI JSON and no-artifact test; typed contract/collector tests. |
| 2 | For a builtin preset copy, the message tells the user to re-run `chrona preset copy <id>`. | Copied-member CLI test, plus a direct-override negative test. |
| 3 | A CLI test covers a stale View, a stale Theme and a stale Layout Profile. | Three parametrized CLI cases using a copied builtin preset. |

The three criteria form one atomic user-facing code slice: publishing only the contract code without the copy remedy would leave the reported workflow incomplete. A separate final review slice records the exact release evidence and closes the issue only after CI.

## I489-1 — Typed refusal and contextual remedy

**Owners/files:**

- `src/chrona/presentation/contracts/resources.py`: derive supported versions from `_SCHEMAS`, detect unsupported declared string versions once for both parser and schema-explanation paths, carry kind/id/found/supported/pointer in a typed error; preserve existing malformed/non-string, unsupported-kind and supported-body behavior.
- `src/chrona/presentation/contracts/diagnostics.py`: collect this typed failure as a resource-local diagnostic and continue sibling validation rather than aborting the collection.
- `src/chrona/presentation/model/closure.py`: preserve `/version` through single-resource, draft and snapshot paths; remove version-only early rejection of validly framed snapshot Layout/Review Detail resources; carry failed declared-preset-member identity to the CLI without command wording. Keep id and content-identity validation.
- `src/chrona/app/cli.py`: only for a local failed declared member of a currently builtin copied preset, append the safe new-directory `chrona preset copy <id>` remedy. An explicitly overridden stale resource gets only the generic version diagnostic.
- `tests/unit/chrona/presentation/contracts/test_contract_resources.py`, `tests/unit/chrona/presentation/model/test_draft_closure.py`, `tests/unit/chrona/presentation/model/test_snapshot_context_closure.py`, and `tests/cli/test_cli.py`: precise code/message/pointer, supported-version derivation, registered-kind coverage, collector continuation, copied-member provenance, override negative, stale snapshot Layout Profile and Review Detail Profile special paths, and all three literal CLI cases. Add only the files actually needed after focused inspection.
- `docs/diagnostics/inventory.md`: regenerate if the new literal diagnostic site changes it; review the changed sites rather than accepting a broad mechanical diff.

**Acceptance gate:** focused tests above; `python tools/diagnostic_inventory.py --check` after regeneration; `python tools/check_issue_acceptance_reviews.py`; current builtin preset copy/render positive cases; public materializer check `python tools/regenerate_public_examples.py --check --jobs 4`; inspect any Scene/SVG differences as one batch and require byte identity unless the design is amended. `git diff --check` and architecture review confirm contracts do not format CLI commands and render layers are untouched. Use the project `.venv` with required `.[dev,render]` and CJK font package; do not run an expensive duplicate full local suite without a specific risk.

**Publication:** one coherent code/test/generated-inventory commit on a clean current-main base, pushed serially after fetching `origin/main` and checking ahead/behind, diff and conflict risk. Inspect the resulting three-OS conformance/full pytest/wheel-smoke and newest-Python public reproduction. A red check is diagnosed before proceeding.

## I489-2 — Literal acceptance and closure

Create `docs/reviews/current/issue-489-resource-version-diagnostics-acceptance-review-2026-09-27.md` using the literal-acceptance template. Record the exact I489-1 commit, focused commands/results, public CLI sample for each stale resource, no-artifact evidence, materializer byte outcome, architecture check, and CI run/PR link. Repeat the three issue criteria verbatim with `met`, `not met`, or `deferred` and direct evidence. Publish this review separately, confirm remote state and its CI, then close #489 only if all rows and release gates are met. Leave reviewer-owned #454 unchanged.

If implementation exposes a version-shape or provenance rule not resolved by the design, stop the code slice, publish a design correction plus architecture re-review and implementation amendment, then resume. Do not add a fallback parser or a local CLI conditional that bypasses the typed error transport.

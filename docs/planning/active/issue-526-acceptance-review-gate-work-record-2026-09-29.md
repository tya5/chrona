# #526 acceptance-review gate work record

## Baseline and design plan

Public `main` is `5408ef2d`. Its #496 review has five literal rows but lacks the validator's issue subsection and programme section. CI [36479216448](https://github.com/tya5/chrona/actions/runs/36479216448) fails conformance on that structure; the earlier #525 PR CI applies to a different commit. No product, schema, or rendered artifact change is required. The reviewer-maintained [board #454](https://github.com/tya5/chrona/issues/454) places this fix before #504/#501.

Literal [#526](https://github.com/tya5/chrona/issues/526) acceptance:

1. Fix the review structure; main CI is green.
2. (Process) Close an issue only after the CI run **of the commit that lands its acceptance review** is green, and cite that run. This is already implied by AGENTS.md ("Do not close a ticket while its required release gate … remains unverified"). It is restated here because it slipped.

Design questions: preserve all five #496 dispositions and evidence while meeting the marked-review grammar; make the closure gate explicit without duplicating policy; determine whether #496 must be reopened until the corrected review's own CI passes. Evidence: focused acceptance checker, full conformance, final-main CI, and issue/commit links. The independently publishable slices are this plan, the design/architecture decision, the implementation plan, the review/process correction, and final acceptance.

## Selected design and architecture review

The marked-review grammar is the authority for the release record: each literal section contains `### Issue #n`, its source and observation date, then the literal table; a `## Programme-level criteria (optional)` section follows. Preserve the five #496 rows without changing product acceptance. The programme section says `None.` because #496 has no additional programme-level criterion. No schema, model, resource, or rendered output changes.

The process failure is separate from the formatting defect. Reopen #496 because its review-bearing main commit failed; reclose it only after the corrected review-bearing main commit's CI succeeds, citing that run in the closure comment. Make AGENTS.md name that exact-commit gate, so successful implementation-PR CI cannot be mistaken for review-publication CI. The #526 final review must likewise land before its own main CI is accepted and the issue is closed. This clarifies the existing publication rule, not a product compatibility contract; no specification or ADR change is warranted.

Whole-architecture check: the correction is confined to contributor procedure and review metadata. Project, View, Theme, Layout, Scene, adapters, schemas, preset resources, and materializer bytes remain unchanged. The acceptance checker should pass without weakening or bypassing its structural rules. Risk: a PR-head green run is insufficient if the eventual main commit includes a new review document; verify the exact main SHA after merge.

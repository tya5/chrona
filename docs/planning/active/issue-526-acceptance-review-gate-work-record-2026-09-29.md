# #526 acceptance-review gate work record

## Baseline and design plan

Public `main` is `5408ef2d`. Its #496 review has five literal rows but lacks the validator's issue subsection and programme section. CI [36479216448](https://github.com/tya5/chrona/actions/runs/36479216448) fails conformance on that structure; the earlier #525 PR CI applies to a different commit. No product, schema, or rendered artifact change is required. The reviewer-maintained [board #454](https://github.com/tya5/chrona/issues/454) places this fix before #504/#501.

Literal [#526](https://github.com/tya5/chrona/issues/526) acceptance:

1. Fix the review structure; main CI is green.
2. (Process) Close an issue only after the CI run **of the commit that lands its acceptance review** is green, and cite that run. This is already implied by AGENTS.md ("Do not close a ticket while its required release gate … remains unverified"). It is restated here because it slipped.

Design questions: preserve all five #496 dispositions and evidence while meeting the marked-review grammar; make the closure gate explicit without duplicating policy; determine whether #496 must be reopened until the corrected review's own CI passes. Evidence: focused acceptance checker, full conformance, final-main CI, and issue/commit links. The independently publishable slices are this plan, the design/architecture decision, the implementation plan, the review/process correction, and final acceptance.

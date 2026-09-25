# Architecture Review — State-Text Contrast Treatment Transport (#431)

**Design reviewed:**
`issue-431-state-text-contrast-transport-correction-2026-09-26.md`.
**Decision:** Accepted correction before report implementation.

| Boundary | Review result |
| --- | --- |
| Theme closure → Scene | The finite resolved treatment is a required completed fact for classified state text. |
| Scene → contrast policy | The evaluator can select its documented floor without role-name inference or Theme re-resolution. |
| Scene → adapter | The field is transport-only; no renderer behavior changes. |
| Existing #446 observations | Unchanged: generic perceptibility remains policy-free and does not consume treatment. |

The correction is narrower than reopening Theme or Layout policy.  It closes an
otherwise unrepresentable report requirement and preserves the #454 rule that
completed-output checks consume completed evidence rather than reconstruct
authoring state.

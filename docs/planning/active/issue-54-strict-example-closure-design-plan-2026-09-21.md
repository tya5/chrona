# Issue #54 strict example-closure design plan

## Trigger

Issue #52 showed that preserving authored identities exposed a previously hidden policy:
the public example materializer always invokes the CLI with strict content-identity
requirements, while checked-in example contexts had been authored unpinned under #44's
opt-in rule. PR #53 supplies complete pins and proves the evidence reproduces, but the
strict-example boundary and missing-pin diagnostics were not specified.

## Decisions to close

1. General render contexts retain #44 opt-in pinning.
2. Canonical checked-in example manifests are strict evidence fixtures: every referenced
   resource and declared font asset is pinned.
3. The public example materializer validates strict completeness before invoking the CLI.
   It reports the missing authored path with `E_CONTENT_IDENTITY_REQUIRED`; it never relies
   on a later font-metrics failure to communicate this condition.
4. A wrong pin remains `E_CONTENT_IDENTITY` (resource) or
   `E_MATERIALIZER_FONT_IDENTITY` (font asset).
5. PR #53's pin-only evidence may merge only after this design and its implementation plan
   are published; generated SVGs remain materializer output only.

## Completion criteria

- The example policy is explicitly separated from #44's general opt-in policy.
- Missing reference and font-asset pins fail before CLI render and identify their path.
- Every canonical manifest context is fully pinned and byte-reproduces without `--write`.
- Tests cover unpinned and wrong resource/font cases.

# Design — starter-compatible elevated preset (#460)

**Plan:** [design plan](../planning/active/issue-460-elevated-preset-starter-design-plan-2026-09-26.md).

The `elevated-light` group-band gradient and shadow are decorative effects.
Its flat fill remains a complete, visible group-band paint. Declare each
effect `decorative-optional` in the Theme, leaving the baseline profile's
existing deterministic omission rule in force. A rich SVG profile retains
both effects unchanged. No adapter substitutes paint and no preset selects a
target: target/profile remain explicit Draft command inputs, as specified by
the preset ingress boundary. This avoids making a reusable appearance bundle
silently change output capabilities or break non-SVG targets.

The shipped library is the test's authoritative enumerator. A conformance or
CLI test reads every library entry, copies it with the public command, creates
one fresh starter project, and renders each copy with the default target and
no profile exception. New library entries automatically enter this test.
Rich-profile output remains independently tested. Required effect rejection
remains a valid capability diagnostic for other Themes and needs a dedicated
fixture rather than a test that assumes `elevated-light` is required.

The flat default is a deliberate visual downgrade, not a hidden capability
upgrade. Documentation will state that rich output requires an explicit
profile. No public schema, preset manifest, or Project migration is required.

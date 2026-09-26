# Design — Exact Proportional Degradation for Missing Tabular Digits (#463)

**Plan:** [design plan](../planning/active/issue-463-tabular-font-degradation-design-plan-2026-09-26.md).
This supersedes the draft-host rejection rule in the #447 host numeric
capability correction only for a face whose proportional digits are exact.

## Use case and selected contract

An author chooses an exact host face such as Hiragino Sans or Georgia for a
bundled Theme. The Theme requests tabular digits for numeric text, but the
selected face cannot provide them. The draft still renders with that face's
actual proportional advances and emits `W_FONT_TABULAR_UNAVAILABLE` naming the
role, selected family and weight. This warning denotes loss of column-digit
alignment, not loss of the digits or a substituted face.

The request remains in the source Theme. Draft font closure computes an
effective per-role numeric spacing from the resolved exact face. It may change
`tabular` to `proportional` only if all proportional digit advances are present.
It retains exact rejection for a missing face, missing basic digits, corrupt
metrics, or any other unavailable mode. No separate `required` syntax or
fallback-family search is added in this issue: both would need a distinct
authoring and identity contract, while the acceptance only requires the
ordinary request to degrade visibly.

The effective role treatment must be consumed by **both** Layout measurement
and completed Text placement/Scene text layout. SVG/PNG must paint the same
`proportional` mode; no adapter may independently fall back. The warning is a
typed, deterministic draft-resolution record, one per affected role/face.
The record has `code`, `role`, `family`, `weight`, `requestedSpacing`, and
`effectiveSpacing`; its code is `W_FONT_TABULAR_UNAVAILABLE`. The CLI emits
that record after successful output and the inspection Scene carries the same
record in an optional top-level `fontWarnings` array (absent for no warnings).
Immutable contexts and packaged metrics never take this path, so public
materializers remain byte-identical.

## Ownership and failure

Theme/Scheme own the declared typography request; host-font closure owns
selected-face capability and effective draft treatment; Layout owns exact
measurement; Scene transports completed effective typography and the warning;
adapters serialize. This extends #410 and #447 without weakening immutable
declared-metrics-v3 validation or #449's distinction between recoverable
presentation degradation and missing resources.

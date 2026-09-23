# I310 Design Correction: Host-Mark-Specific Inside Label Roles

## Supersedes

This correction supersedes the single `textOnMark` intent proposed in
`i310-inside-label-contrast-design-correction-2026-09-23.md`.

## Trigger

The public Schemes contain both light and dark comparison fills.  A single
inside-label ink cannot meet a 4.5:1 contrast ratio against every planned,
actual, snapshot, and scenario fill without changing established palette
meaning.  This is a real domain distinction, not an adapter limitation.

## Corrected design

The semantic registry declares four host-mark-specific inside-label semantics:
`memberLabelInsidePlanned`, `memberLabelInsideActual`,
`memberLabelInsideSnapshot`, and `memberLabelInsideScenario`.  Each has a
distinct Theme fill role.  Theme binds each label role to an appropriate Scheme
intent and Theme resolution validates that pair against its corresponding mark
role at a minimum contrast ratio of 4.5.

Layout still selects only the measured `inside` rung and records that choice.
It does not select ink or know Scheme values.  Scene combines the selected rung
with the already-known host mark semantic to select one registry entry.  This
is semantic projection, not a renderer policy.  A non-inside label continues
to use `memberLabel`.

The Scheme keeps its existing semantic palette; no generic `textOnMark` intent
is added.  Public Themes declare the four explicit bindings.  The Theme
resolver rejects a missing binding, non-color token, or unsafe host/label pair
with `E_SCHEME_INSIDE_LABEL_CONTRAST`.

## Architecture review

This preserves the ownership sequence: View requests placement, Layout proves
fit and records the rung, Scene projects a closed semantic role from that rung
and host mark, Theme/Scheme resolves and validates ink, and renderers serialize
the result.  It avoids palette distortion, literal primitive colors, and
renderer-local contrast decisions.

## Implementation amendment

I310 replaces the single-role implementation with the four-role registry and
pairwise Theme contrast validation.  The View vocabulary and the rule that
`auto` never adds `inside` remain unchanged.

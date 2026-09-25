# Design Correction — Builtin Presets Must Be Project-Generic (#378)

**Status:** Proposed for architecture review.

## Discovery

The first I378-1 execution copied the HALCYON mission-light preset into an
empty directory and rendered the #376 starter through the ordinary `--preset`
resolver.  It correctly failed `E_REVIEW_EMPTY`: the gallery View selects
HALCYON object identifiers.  A gallery appearance Context is evidence for a
look, not proof that its View is reusable for an arbitrary Project.

## Correction

Every builtin catalogue entry must be a complete **project-generic** bundle.
Its View selects planned spans and points without project ids, domain fields,
or fixed dates; its Layout has only sources available to such a View; its Theme
and Scheme supply the appearance.  The gallery continues to link visual
evidence, but no copied bundle may retain a corpus-specific selection rule.

The five catalogue looks are therefore authored as canonical package bundles,
not copied from the gallery Context resource paths.  Their source files may
reuse compatible literal/theme data only after independent generic-render
validation.  The explicit copy command writes `preset.yaml` at the copied root
and the referenced member paths below it, so the existing safe relative
`--preset` resolver remains unchanged.

## Required proof

For every catalogue id, initialize the minimal starter, copy the bundle, and
render it through `--preset`.  Assert an SVG with all three starter object ids;
compare its Scene/SVG to a no-preset baseline only for the intended visible
appearance difference.  A corpus-specific View is a rejected library fixture,
not a fallback candidate.

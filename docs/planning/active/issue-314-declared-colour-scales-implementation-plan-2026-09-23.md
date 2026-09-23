# Issue 314 Declared Colour Scales Implementation Plan

## Preconditions

Implement Specification 60 as one atomic resource-contract migration.  Do not
retain a v0.1/v0.3 reader, the hash category resolver, free-string scale
legend, or the removed rule engine.

## Slices

1. **Typed resource migration.** Introduce the successor View, Theme, and
   Color Scheme schemas and immutable runtime contracts.  Validate tagged field
   sources, unique View domains, exact Theme domain mappings, named Scheme
   slots, and stable diagnostics.  Replace current resources and Context
   closure references together so every public Context remains materializable.
2. **Resolved encoding closure.** Replace `category_index` and the `category`
   binding with a typed resolved scale table.  Build it from pinned View,
   Theme, and Scheme inputs and validate every selected eligible object before
   Scene construction.  Add focused malformed-domain, missing mapping/slot,
   missing field, and unknown-value tests.
3. **Appearance completion and derived legend.** Carry only typed resolved
   scale values to the Scene paint-completion boundary.  Apply a value-specific
   fill to eligible planned member marks; derive present-domain legend entries
   before Layout.  Delete the hand-written legend path and prove Layout receives
   content, while Scene receives completed geometry and concrete paint.
4. **HALCYON evidence and release gate.** Migrate HALCYON’s category bands to
   named scale slots and add a public non-default field-encoding example.
   Regenerate public SVGs, run focused tests, full pytest, conformance,
   materializer byte comparisons, source-boundary tests, and isolated wheel
   smoke.  Review generated diffs for intentional scale/legend changes.

## File-level scope

Expected owners are `schemas/view-*`, `schemas/theme-*`,
`schemas/color-scheme-*`, `presentation/contracts/resources.py`,
`presentation/color_scheme.py`, `presentation/model/closure.py`,
`presentation/review/v05_content.py`, `presentation/scene/*`, and the public
example resources/generated evidence.  Layout's placement algorithms and
renderer adapters are not scale evaluators.

## Acceptance

* Each used value maps by explicit key to exactly one named Scheme slot.
* An absent/unknown value or incomplete mapping rejects rather than repainting.
* Scene/adapters cannot hash, parse, or fallback a scale.
* Scale legend entries exactly match used values and completed swatches.
* All public contexts materialize after the one-step migration.

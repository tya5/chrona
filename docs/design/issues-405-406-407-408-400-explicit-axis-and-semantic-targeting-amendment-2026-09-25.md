# Explicit Axis and Semantic Targeting Amendment (#405, #406, #407, #408, #400)

**Status:** Accepted before completing the atomic I2/I3 unit.

## Explicit axis ownership

`timeline-axis` is a required table-timeline surface slot.  A View that uses
that surface must therefore declare a non-empty ordered `axis.tiers` sequence.
There is no implicit level, band, grid, label form, or locale default.  This
removes the final positional/default axis reader rather than making an empty
axis appear to be a valid authored surface.

All shipped table-timeline Views migrate in the atomic unit.  Their declarations
make each intended band, grid, and label tier explicit.  A missing or empty
axis is rejected at normalized View ingress before Layout allocation.

## Semantic visual targeting

Visual requests target author-visible axis facts, not internal placement-ID
spelling.  `axis-band {level, index}` and `axis-label {level, index}` resolve
in Layout against typed axis tier/interval metadata.  Layout then supplies the
chosen completed placement identity to icon placement.  Scene never parses an
axis ID and adapters see only completed icon geometry.

The selector's `level` is the selected concrete unit for an auto label tier,
and `index` is the natural interval index.  A selector must match exactly one
completed, non-thinned target; otherwise it diagnoses `E_LAYOUT_VISUAL_TARGET`.
This preserves a stable authoring vocabulary while allowing role-specific
placement identities to remain implementation-owned.

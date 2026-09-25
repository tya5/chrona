# I2 Implementation Amendment — Role-Specific Axis Layout (#405, #406, #407, #408, #400)

**Entry:** I1 is merged at `dafed01c`.

The accepted v0.17 contract replaced a multi-role tier with a single-role tier
and moved label properties beneath `label`.  I2 must consume that contract
directly; it must not reconstruct positional `levels`, infer roles from array
order, or retain the I1 bridge after this slice.

1. Add typed axis-tier, candidate-form, interval, and recorded-outcome values
   to the Layout request/result boundary.  View normalization preserves the
   declared order but does not choose geometry.
2. Extend calendar interval generation for `half` and calendar-owned fiscal
   quarter/half/year origins.  Keep ISO weeks; do not add project-relative
   weeks.
3. For every concrete tier, apply `every`, calculate its role-specific
   placement, and make each tier observable in Layout output.  Separate
   band/grid/label placement identities and Scene roles.
4. For `unit: auto`, evaluate only the explicitly declared candidate forms in
   dense-to-coarse order using measured formatted labels; record the selected
   candidate.  Do not use a process locale or undeclared fallback.
5. Move axis label measurement, fit, alignment, and thinning-record production
   into Layout.  I3 will connect the result to the shared visible/invisible
   failure registry; I2 must expose enough structured outcome data for it.
6. Remove the I1 legacy internal bridge in the same PR.  Add focused unit,
   placement/projection, and corpus tests for three roles, every-N, auto,
   half-year, fiscal April, locale-independent forms, and all tier consumption.

Acceptance is a renderer-neutral complete axis placement closure: Scene only
projects bands, grids, and text already selected and positioned by Layout.

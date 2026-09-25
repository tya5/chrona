# I1 Acceptance Review — Axis and Calendar Contract Migration (#405, #406, #407, #408, #400)

**Result:** Accepted as I1 only.

## Delivered closure contracts

* `chrona/view/v0.17` is the sole runtime View ingress.  It replaces positional
  `levels`, dead `ticks`, and `timePresentation.axisLevel` with one-role axis
  tiers.  Label forms are unit-valid; automatic labels declare their finite
  candidate-form map.
* `timeline/v0.7` is the sole Project ingress and adds calendar-owned
  `fiscalStartMonth` with the schema default of January.
* `chrona/profile/v0.3` requires Project v0.7.  The Project/Profile pair moves
  atomically, so a pinned profile package cannot claim compatibility with an
  obsolete Project contract.
* All corpus sources, conformance cases, resource inventories, package
  bindings, direct validation callers, and generated closure evidence use the
  three new versions.  No runtime, corpus, test, or tool ingress for the
  retired versions remains.

The profile package's self identity was recalculated over canonical YAML with
its self field omitted, and the Project's immutable external reference was then
recalculated over the exact updated package bytes.  This preserves both layers
of identity binding.

## Boundary review

View owns finite intent; Project calendar owns fiscal origin; Layout remains
the future consumer of intervals, labels, and placement outcomes; Scene and
renderers have no new policy.  The I1 normalization bridge accepts only the
new typed contract and exists solely until I2 replaces the old internal axis
composition input.  It does not read a legacy public field.

No visible policy changed: regenerated public SVG bytes are unchanged.  Scene
provenance changed only because the closed source contracts and exact resource
identities changed.

## Evidence

* focused schema/contract/content tests: 69 passed;
* materializer, package, and conformance checks: 38 passed;
* schema-reference and corpus-coverage checks: 31 passed;
* full suite: 813 passed, 19 skipped;
* installed-wheel smoke: passed.

I2 still owns half/fiscal interval calculation, auto/every-N fitting,
role-specific placement, and every-tier consumption.  I3 still owns the
visible/invisible failure registry and recorded suppression policy.  Therefore
this review does not close #400 or #405–#408.

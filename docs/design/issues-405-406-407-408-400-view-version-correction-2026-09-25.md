# Design Correction — Axis View Version (#405, #406, #407, #408, #400)

**Status:** Accepted correction before I1 implementation.

The axis design's new typed tiers are a source-contract replacement, not an
interpretation of the existing positional fields. Because `chrona/view/v0.16`
is already a published runtime ingress, the replacement is
`chrona/view/v0.17`, not an in-place v0.16 rewrite.

v0.17 removes `axis.levels`, `axis.ticks`, and `timePresentation.axisLevel`.
It introduces the accepted typed tier declaration and associated finite
failure-policy inputs. All corpus Views, Context closure identities, schema
inventory, package resources, tests and generated evidence migrate atomically;
v0.16 has no runtime reader after I1. This preserves a clean source boundary
without a compatibility shim or an ambiguous version meaning.

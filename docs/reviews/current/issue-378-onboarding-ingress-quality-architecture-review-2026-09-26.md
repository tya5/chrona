# Architecture Review — Onboarding Ingress and Publication Quality (#378)

**Result:** Accepted for correction implementation.

The import-direction check identifies an actual `operational` ↔ `usecases`
cycle. Catalogue schema validation belongs to the presentation preset copy
use case with schema bytes supplied by `resources`; removing the operational
parser dependency restores the intended inward dependency direction. The
package catalogue does not acquire operational revision or store semantics.

Schema annotations, declared identity classification, and generated command
and diagnostic documents are existing governance contracts. Repairing their
evidence is required for publication and does not alter the product contract.
The correction is consistent with specification 09's application boundary,
specification 46's completed-paint boundary, the #378 onboarding design, and
the source/effective identity correction already published for I378-2.

An accepted design document cannot stand in for a green conformance run. The
corrected implementation must prove the full check catalogue and public
materializers before #378 is accepted.

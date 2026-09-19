# M9 Release-Acceptance Design Review

**Date:** 2026-09-19  
**Disposition:** Pass — implementation may begin only according to the documented plan.

## Reviewed boundary

The former FD-5 text required an acceptance manifest but left its structure and the
meaning of an exclusion unspecified. `release-acceptance-v0.2.schema.yaml`, its
fixture, and `validate_release_acceptance.py` now make the complete input closure,
target version, UC-01–UC-15 coverage, reproducible evidence, and exclusions explicit.

## Finding

The fixture exposes one real delivery gap: UC-06 is `excluded`, because this repository
does not yet provide M5's AI Command-proposal adapter or authorization-policy
integration. This is not an output-adapter defect and must not be hidden by M9 SVG
success. The target-package runtime check may follow this design gate, but M9 remains
in progress until UC-06 is delivered and the manifest has no exclusions.

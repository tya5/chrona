# Design Correction Plan — Axis Tier Role and Label Contract (#405, #406, #407, #408, #400)

**Trigger:** The unpublished I1 scaffold admits a list of roles and one global
label-form enum.  That contradicts the accepted design: a tier has exactly one
job, and a label form must be meaningful for its calendar unit.

1. Publish the corrected role-specific tier contract and its architecture
   review before changing the schema or corpus.
2. Amend I1 so v0.17 has one role per tier and role-specific properties; remove
   the invalid unpublished `roles` shape rather than supporting both shapes.
3. Implement schema and typed-normalization validation together, migrate every
   corpus View atomically, and add negative tests for role/form/auto misuse.
4. Leave interval selection, label fitting, fiscal bucketing, and diagnostics
   to I2/I3; I1 establishes their unambiguous source contract only.

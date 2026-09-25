# I1 Implementation Amendment — Axis Tier Role and Label Contract (#405, #406, #407, #408, #400)

Replace the unpublished v0.17 `roles` list and global `form` with the accepted
single-role, role-specific tier union.  Update typed View normalization and
negative contract tests with schema validation; migrate every corpus tier into
one band/grid/labels declaration per role.  Test invalid unit/form pairs,
multi-role remnants, label properties on non-label roles, and auto outside the
explicit label-candidate form.

This amendment is part of the existing atomic I1 View v0.17 / Project v0.7 /
Profile v0.3 release.  It does not implement I2 fitting/bucketing or I3
diagnostics, and it adds no v0.16 reader.

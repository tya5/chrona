# Explicit Axis Ingress Scope Amendment (#405, #406, #407, #408, #400)

**Status:** Accepted correction.

The explicit-axis rule applies to shipped table-timeline View resources and
their corpus acceptance evidence.  It does not make optional axis content a
precondition of the generic normalized content seam: that seam is also used to
test table, relation, annotation, and summary facts independently of a
rendered axis.  Schema-level mandatory-axis migration, if adopted, must be a
separate versioned View-contract change with its own fixture migration.

Consequently this programme migrates every shipped View that declares the
required `timeline-axis` slot, but does not add a runtime normalizer guard that
turns unrelated content tests into axis validation.  The Layout/Scene boundary
and semantic visual-targeting decision are unchanged.

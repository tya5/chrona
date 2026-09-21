# ADR-0027: Give the local Actual Store an explicit immutable CAS layout

**Status:** Accepted  
**Date:** 2026-09-21

## Decision

For M26's local-only Store profile, an Actual-set reference names
`<root>/<revision-token>/<address>`. The address is `actuals/<actual-set-id>.yaml`.
The mutable implementation pointer is only `<root>/actual-tips/<actual-set-id>.json`;
it is never accepted as a Command input. A write verifies the pointer equals the
reference token, creates the complete new token directory and canonical Actual-set
file, then atomically replaces the pointer. Failure leaves no new pointer.

Store provisioning initializes the pointer out of band by naming one already verified
immutable Actual-set reference. An M26 command never creates a missing pointer. A
missing pointer rejects as a target-closure failure, so first use cannot silently turn
an arbitrary file into a mutable Actual Store.

## Consequences

- Every accepted intake/reconciliation command returns a new immutable resource
  reference which can be used by later commands and CI.
- `store-config` roots are sufficient for both read and CAS write without a hidden
  working-tree path.
- This is an adapter layout, not a Project or Actual semantic format.

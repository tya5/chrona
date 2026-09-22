# Issue 99 Step 4 / C99-4B — Optional Review Contract Design

**Status:** Proposed design.  **Predecessor:** C99-4A, merged by PR #129.

## Decision

C99-4B removes `OpaqueResourceContract` from the render closure.  Every
remaining closure resource is accepted by an exact kind/version schema and is
represented by a named frozen contract: `ActualSetContract`,
`SnapshotRefContract`, `ProfilePackageContract`, `SummaryProfileContract`, and
`ReviewDetailProfileContract`.  The named snapshot project retains
`ProjectContract`; it is not a second generic resource form.

Schema acceptance remains authoritative.  A schema referenced through an
external `$id` is loaded into the same local schema registry; a missing exact
schema is a design blocker, never an opaque runtime fallback.

## Consumer boundaries

| Consumer | Typed inputs after C99-4B | Retained owner |
| --- | --- | --- |
| render use case | `RenderClosure`, profile package contracts, actual/snapshot contracts | pipeline order and input-read ledger |
| projection | `ProjectContract`, `ViewContract`, `ActualSetContract`, optional snapshot `ProjectContract` | scheduling/comparison facts |
| review content normalization | `ProjectContract`, `ViewContract`, `ActualSetContract`, detail/summary contracts | display-policy normalization |
| extension validation | `ProjectContract` and profile package contracts | extension semantics |
| Layout / Scene / renderer | no resource contracts | unchanged completed seam |

Detailed semantic facts continue to be frozen mapping payloads owned by their
domain consumers.  The consumers no longer receive generic closure envelopes,
perform kind-string lookup, or access `ClosureResource.contract.document`.

## Exact acceptance inventory

| Kind/version | Schema |
| --- | --- |
| actual-set/v0.1 and v0.2 | `actual-set-v0.1.schema.yaml`, `actual-set-v0.2.schema.yaml` |
| snapshot-ref/v0.2 | `snapshot-ref-v0.2.schema.yaml` plus revision-store reference schema |
| profile-package/v0.1 | `profile-v0.1.schema.yaml` |
| summary-profile/v0.1 | `summary-profile-v0.2.schema.yaml` (its declared exact version) |
| review-detail-profile/v0.1 | `review-detail-profile-v0.1.schema.yaml` |

If any public resource fails this inventory, first publish a schema/resource
correction like PR #128; C99-4B may not add an acceptance exception.

## Acceptance and publication

- No `OpaqueResourceContract` or unknown-version fallback remains.
- Optional contracts are schema-first, frozen, and retrieved through typed
  `RenderClosure` accessors.
- Projection/content function signatures accept contracts rather than generic
  resource mappings.
- Absent optional inputs retain their existing behavior and diagnostics.
- Five materializers retain byte identity; full tests, conformance, structural
  source checks, import/reachability lint, and generated-SVG diff pass.

The implementation plan is published separately.  C99-4C begins only after
this slice is merged.

# C-GDF-1 Implementation Plan: Corpus Hygiene and Preset Evidence

**Status:** Complete  
**Implements:** #348 correction, Specification 32 topology correction

## Design decision

The legacy Controller Z `variants/` tree is neither manifest-declared nor
materializable, and contains stale source/renderer artifacts. It cannot be
made authoritative by adding a discovery exception. It will be removed. The
corpus retains only declared Contexts and materializer-generated SVG evidence.

A committed ordinary presentation preset is evidence of a reusable named
presentation point, not a package or guided workspace resolver. It must name
only existing View/Theme/Scheme/Layout resources and be verified against the
existing Context's immutable resource identities. It cannot carry Project,
Actual, renderer, package, lock, or path-resolution authority.

## Implementation and acceptance

1. Update Specification 32 and Controller Z documentation to remove the
   obsolete variants contract.
2. Delete the entire legacy `variants/` tree in one reviewable change.
3. Add `examples/controller-z/presets/executive-light.yaml`, using the existing
   typed preset contract and ordinary presentation resources.
4. Add a focused evidence test that parses the preset and proves its declared
   resource IDs/bytes equal the existing Executive Context references.

Acceptance requires no tracked Controller Z variants path, no residual
documentation/reference, one schema-valid public preset, and evidence that it
names the already materializable Executive presentation closure. No generated
SVG changes occur in this slice.

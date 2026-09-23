# I-GDF-2 Declarative Package Contract Review

**Date:** 2026-09-23  
**Scope:** `presentation-package/v0.1` schema and pre-acquisition source-tree validation
**Decision:** Accepted

## Architecture conformance

Package validation is a pre-acquisition boundary.  It accepts a declared root,
checks a closed manifest and exact member bytes, and validates each member as
an existing ordinary View/Layout/Theme/Scheme/Presentation Preset contract.
It does not construct a RenderClosure, normalize a workspace, load a Context,
or import Layout/Scene/renderer code.

The validator enforces the canonical package topology, no symlinks, no
undeclared files, and no executable/raw-renderer escape hatch.  It checks the
corrected framed aggregate identity and every literal member digest.  Presets
refer to manifest-listed ordinary members from the package root; they add no
new override vocabulary.

## Evidence

- Package fixtures prove complete verification and member lookup.
- Tampering a member is rejected before a consumer can use it.
- An undeclared executable file is rejected.
- Schema inventory and annotation gates include the new public schema.

No package directory is yet acquired, cached, selected by a workspace, or
used for rendering.  Those authority transitions remain I-GDF-3 and I-GDF-4.

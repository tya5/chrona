# Design Plan — Draft System-Font Provider (#411)

**Status:** active; implementation is not authorized by this document.

## Trigger

The current Context font closure supports only copied Context bytes and
registered package bytes.  Consequently a user who owns a commercially
licensed installed face must copy it into a project to obtain a PNG, despite
the fact that the author needs only a local shareable raster artifact.  The
existing prohibition protects immutable reproduction, but incorrectly applies
that constraint to the draft authoring path as well.

## Scope

The design must add a draft-only `system` font provider that resolves a
requested family and weight to one installed host face, reads metrics from
that exact resolved file before Layout, and permits the PNG renderer to use
the same face without copying it into the project.

An immutable Render Context and materializer must continue to require only
Context/package identity-pinned assets.  A system-font draft must be visibly
classified in closure/provenance and rejected before immutable rendering or
materialization.  Missing or ambiguous requested faces must diagnose rather
than silently substitute.

## Non-goals

This work does not make host fonts portable, add a renderer fallback, loosen
immutable font-byte identity, alter Theme typography policy, embed a font in
SVG/PDF, or silently select a system default.  It also does not claim that a
family name alone is reproducible across machines.

## Design questions to close

1. Define the versioned draft-only font locator syntax.  It must name family,
   requested weight/style and provider intent without pretending that a host
   path or content identity was authored.
2. Define a platform-neutral discovery port and its platform implementations.
   A successful result must return one canonical file, actual family/weight,
   source identity, and metrics; an absent, multiple, or incompatible result
   must have a stable diagnostic with the requested family.
3. Define how metric extraction from an installed OpenType face reuses the
   existing `FontMetrics` measurement contract, including numeric advances,
   glyph availability, cap height, and exact source identity.
4. Define closure state that distinguishes a system-font draft from immutable
   closure without allowing the volatile host path to become an immutable
   resource locator or public corpus provenance.
5. Define renderer behavior: SVG uses completed geometry as today; draft PNG
   must pass exactly the resolved system file to resvg, with host fallback
   disabled.  Decide the PDF/typesetter disposition explicitly.
6. Define ingress boundaries: which draft command/context forms can select a
   system descriptor; where `resolve_render_context`, `render-review`, and
   `materialize` reject it; and how those failures name the family.
7. Define testability across CI, where a deterministic installed test font may
   be unavailable.  Tests must use a discovery seam and a local real-face
   fixture without asserting that CI hosts a particular commercial font.

## Required design outputs

The completed English design must include a versioned contract/migration,
typed discovery and metrics model, lifecycle/provenance state machine,
renderer handoff, diagnostics, test matrix, and an architecture review against
the Context/closure/Layout/Scene/adapter boundaries.  It must explicitly
evaluate fontconfig, CoreText, and Windows discovery rather than treating a
single host command as a portable product capability.

## Publication sequence

1. Publish this plan.
2. Publish the complete design and architecture review.
3. Publish an implementation plan split into contract/discovery, closure and
   renderer policy, and draft acceptance slices.
4. Implement only the approved plan, verify draft behavior and immutable
   rejection, then publish the release and its acceptance review.

## Planning acceptance

The phase is ready for design only once a future implementation cannot enable
host fallback in an immutable renderer or select an installed face without
Layout measuring that exact face.

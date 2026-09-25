# Implementation Plan: Presentation capability ceiling (#391)

**Status:** Accepted.

**Implements:** [#391 capability-ceiling design](../../design/issue-391-presentation-capability-ceiling-design-2026-09-25.md)

## I391-1 — One typed capability registry

Create a renderer-neutral `presentation.scene` capability registry with finite
definitions for identity, primitive family, disposition, owning layer, reason,
and issue/design reference.  Export only admitted runtime capability IDs for
Scene/profile validation.  Move the current rich-paint, mark-geometry, and icon
capability group construction to consume that registry; do not duplicate a
second set in target-profile code.

**Acceptance:** every current profile resolves exactly its present supported
admitted IDs; the registry contains every current/deferred/rejected ceiling row;
and no target adapter imports it.

## I391-2 — Substitution admission guard and documentation

Represent substitution as a capability-policy disposition, not an accepted raw
Theme/Scene enum.  Add a deterministic guard proving that no current treatment
can request substitution without a concrete capability-specific alternative.
Publish the generated/checked ceiling document and link it from the visual
capability specification.

**Acceptance:** attempted unowned substitution rejects before an adapter;
existing `required` and `decorative-optional` fixtures retain their behavior;
the documented ceiling stays synchronized with the typed registry.

## I391-3 — Verification and release

Add focused registry/profile/paint tests, regenerate authoritative generated
documentation, run Scene schema/conformance and full tests, public materializer
checks, structural dependency checks, wheel smoke, generated-SVG review, and
three-platform CI.  Publish an English acceptance review and close #391 only
after CI passes.

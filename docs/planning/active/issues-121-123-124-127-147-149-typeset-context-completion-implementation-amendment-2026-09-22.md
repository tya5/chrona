# Typeset Context Completion Implementation Amendment

## Preconditions

Merge the accompanying Typeset Render Context Completion Design Correction.

## Implementation sequence

1. Add Render Context v0.8 with the target-specific typesetter/text-mode
   invariants, update the schema registry and exact inventory, migrate every
   committed Context and draft builder, and remove v0.7 acceptance.
2. Add typed `TypesetterIdentity` data to the Render Context contract and one
   shared renderer-environment projection so every caller passes rasterizer or
   typesetter identity without hand-built divergent dictionaries.  Draft
   ingress obtains `typst` or `tectonic`'s exact installed version and rejects
   absence with `E_RENDER_TYPESETTER_UNAVAILABLE`.
3. Add one pure positioned-source adapter for Typst and one for TikZ, register
   them with empty capability sets, add CLI format choices, and retain all
   existing SVG/PNG/PDF routes.
4. Add schema, closure, capability, source signature/order/identity, positioned
   text, artifact-writing, and optional exact-toolchain compilation tests.
   Run focused tests, then the complete suite and one batched public
   materializer/generated-SVG verification.

## Acceptance

No v0.7 parser or inventory route remains; a typeset Context has an exact,
non-sentinel descriptor; uninstalled draft engines reject deterministically;
the adapters have no forbidden architectural imports; source is stable UTF-8
and preserves completed placement order; and existing public materializers
remain SVG-identical.

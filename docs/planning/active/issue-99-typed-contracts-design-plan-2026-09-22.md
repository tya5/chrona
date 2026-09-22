# Issue 99 Step 4 — Typed Closure Contracts Design Plan

**Status:** Proposed design plan.  **Issue:** #99.  **Predecessors:** #105,
#113, and #114, merged into `main`.

## Problem

`resolve_render_context` currently validates only the render-context document,
then returns mutable YAML mappings in `ClosureResource.value`.  The render use
case, projection, content normalization, layout-profile resolver, and theme
resolution each consequently interpret resource keys for themselves.  This
makes a schema-valid closure insufficiently explicit at the boundary where
untrusted serialized resources become runtime inputs.

## Decision

The schema is the sole authority for resource acceptance and diagnostics.  A
typed contract is the immutable runtime representation constructed *after* the
applicable schema has accepted the decoded document.  It is not a competing
validator and it must not silently recover, add defaults, or redefine schema
semantics.

The closure boundary will therefore:

1. decode YAML into an untrusted mapping;
2. select and validate the exact resource schema for its declared kind and
   version, retaining the existing stable closure diagnostic for rejection;
3. construct a frozen, kind-specific contract from that accepted value; and
4. expose only those contracts to the render pipeline.

The raw mapping ends at this boundary.  Parsing is allowed to reject an
otherwise schema-valid value only for an invariant that JSON Schema cannot
express; such a case requires a named diagnostic and a corresponding schema
follow-up.  No such invariant is introduced by this step.

## Contract model

All closure entries retain immutable identity metadata (`kind`, `id`,
revision, and content identity) and carry a `Contract` rather than a generic
dictionary.  The first complete family is the review rendering closure:

| Contract | Runtime responsibility | Main consumer |
| --- | --- | --- |
| `RenderContextContract` | declared references, target and environment | render use case |
| `ProjectContract` / `SnapshotContract` | scheduled semantic facts | scheduler and projection |
| `ViewContract` | selection and presentation policy | projection and content normalization |
| `ThemeContract` / `ColorSchemeContract` | unresolved decorative declarations | theme resolution |
| `LayoutProfileContract` | layout grammar | layout resolver |
| `ActualSetContract` | observations and as-of fact | projection and content normalization |
| `SummaryProfileContract` / `ReviewDetailProfileContract` | optional review content | content normalization |
| `ProfilePackageContract` | extension package declaration | extension validation |

Contracts may contain immutable mappings and tuples only where the underlying
schema permits open-ended semantic payloads.  Their public API names those
payloads and never exposes the original YAML envelope.  Dates and other
domain-value conversion remain in their existing domain owners; this step does
not move scheduling, projection, layout, Scene, or renderer policy.

`ResolvedTheme` is a separate frozen derived value.  It is built from the
typed theme and color-scheme contracts during closure resolution, so a caller
cannot provide an unrelated mapping under `resolvedTheme`.

## Boundary and ownership review

| Boundary | Decision |
| --- | --- |
| storage → core port → closure | `SnapshotReader` supplies bytes only; no adapter imports a presentation contract. |
| closure → use case | one resolved, immutable `RenderClosure`; the use case cannot inspect YAML envelopes. |
| use case → scheduler | project/snapshot facts are supplied in the scheduler's existing semantic shape through contract-owned accessors; scheduling authority does not move. |
| use case → presentation | view, optional profiles, resolved theme, and layout profile are typed inputs; layout remains the geometry owner and Scene remains projection-only. |
| schema → contract | schemas decide acceptance; contracts preserve accepted facts and make runtime ownership explicit. |
| renderer | consumes completed SceneSurface only; this step gives it no resource/schema access. |

This preserves the source direction established by #113 and the product seam
recorded in Specification 08: `Layout → Scene → renderer`.  It also does not
alter the semantic, slot, or primitive registries established by #114.

## Delivery slices

The work is intentionally split at independently reviewable, behaviour-
preserving publication boundaries.

1. **C99-4A — foundation and mandatory contracts.** Add the immutable contract
   module, exact-schema registry, frozen identity envelope, and a `RenderClosure`.
   Migrate render context, project, view, theme, color scheme, and layout profile.
   Add closure tests proving schema rejection precedes construction and that no
   mutable YAML object escapes.
2. **C99-4B — optional review contracts.** Migrate actual set, snapshot,
   snapshot project, profile package, summary profile, and review-detail profile.
   Make content normalization and projection accept typed inputs only.  Preserve
   the current optional-input diagnostics and output bytes.
3. **C99-4C — closure consumer completion.** Remove `ClosureResource.value` and
   generic resource access from the render use case.  Add structural tests that
   production closure consumers do not accept `Mapping[str, Any]` as a resource
   contract.  Exercise all five public materializers and the input-read ledger.

No implementation slice may add a new schema version, visual policy, layout
policy, compatibility shim, or regenerated public SVG.  A schema limitation
found while implementing reopens this design plan rather than being hidden in
a parser.

## Acceptance evidence

- Each loaded closure resource is schema-validated by its exact declared
  kind/version before a contract exists.
- Contracts and closure metadata are frozen; mutating decoded YAML after
  construction cannot change a render.
- The use case, projection, and review-content path receive typed contracts,
  not generic resource envelopes or YAML dictionaries.
- Existing stable closure diagnostics and all five materializer SVG bytes are
  unchanged.
- Focused contract tests, full `pytest`, schema/conformance checks, import
  direction and reachability checks, public materializer checks, and a
  generated-SVG diff all pass.

## Publication gate

This design plan and its cross-architecture review are published and merged
before C99-4A implementation planning begins.  C99-4B and C99-4C each require
the preceding slice to be merged.  Step 5 begins only after C99-4C is merged.

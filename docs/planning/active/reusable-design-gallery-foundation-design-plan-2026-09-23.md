# Design Plan: Reusable Design Gallery Foundation

**Status:** Active  
**Date:** 2026-09-23  
**Related:** Specification 55, Specification 58, #338, #343, and conditionally #345

## Objective

Create the architectural and evidence foundation for a gallery whose displayed
designs are reproducible Chrona resources that users can later reuse, fork,
materialize, and package.  The first gallery expansion must not create an
independent renderer, a hand-authored SVG collection, a second presentation
model, or a source-tree convention that conflicts with the eventual
Presentation Package contract.

## Verified starting point

- Specification 58 defines the gallery as documentation that references a
  declared regression-corpus slide; the materializer remains the sole producer
  of committed SVG evidence.
- `docs/gallery/example-gallery.yaml` currently contains four provenance-checked
  slide references.  It has no reusable-design metadata or Design Space view.
- Specification 55 defines the Design Space taxonomy and explicitly permits a
  read-only `PresentationDesignSummary`, but #338 deliberately added no
  consumer, schema, command, or UI.
- Existing View, Layout Profile, Theme, Color Scheme, preset, guided
  normalization, Context, Layout, Scene, and renderer contracts are the only
  presentation authority.  A summary must derive from them and retain their
  identities.
- #343 is open and proposes declarative Presentation Packages.  Its design,
  rather than a Registry implementation, is the prerequisite for committing a
  substantial reusable-design source collection.
- #345 is open.  The current portable Scene vocabulary is intentionally closed.
  Rich SVG-only techniques must not be introduced merely to make gallery images
  attractive.

## Architectural constraints

1. Project, Actual, calendar, scheduling, and dependency semantics remain
   independent of gallery choice and package provenance.
2. View owns content and semantic presentation intent; Layout Profile owns
   composition; Theme and Color Scheme own appearance; Layout owns measured
   geometry; Scene is derived; renderer adapters serialize only completed Scene.
3. Gallery metadata is documentary and inspection-only.  It cannot select
   renderer policy, modify a closure, replace a resource reference, or supply
   defaults.
4. A Design Space summary is derived from validated effective resources.  It is
   not a closure input, mutable catalog selector, generic override map, or a
   duplicate flat presentation schema.
5. Every displayed artifact must trace to an immutable corpus Context and a
   public materializer result.  Raster previews, if any, are derived review
   artifacts rather than separate authored evidence.
6. A reusable Presentation Package is declarative.  It contains no executable
   plugin, raw SVG/XML, network fetch, host-default dependency, or moving
   `latest` reference.
7. New visual expression may use only the present portable capability set until
   #345 admits and specifies another one.  No gallery asset may establish an
   SVG-specific escape hatch.

## Ordered design work

### GDF-1 — Design Space consumer and specification correction

Select the gallery as #338's first bounded consumer.  Reconcile Specification
55's resource-version references with the current live contracts, without
altering the ownership taxonomy.  Design a read-only
`PresentationDesignSummary` projection for a resolved ordinary resource bundle.

The design must specify:

- the finite summary fields mapped to Content, Composition, Visual Grammar, and
  Appearance;
- source resource identity/provenance for each displayed value;
- how summaries work for explicit and guided/materialized closures without
  invoking a second resolver;
- which taxonomy values cannot yet be summarized and therefore must be absent,
  not guessed; and
- stable inspection diagnostics for incomplete/unsupported summary input.

Acceptance: paired, identical Project/schedule fixtures can expose distinct
validated design summaries and closures; no summary changes semantic identity,
geometry, Scene, or rendered bytes.

### GDF-2 — Gallery curation and evidence contract

Extend the Specification 58 gallery contract from a flat slide index to a
provenance-checked design comparison surface.  Define catalog fields for
editorial intent, audience, comparison axis, source corpus/slide, derived
Design Space summary reference, target/capability statement, and accessibility
notes.  Only corpus/slide identity is evaluation-relevant; the other fields
are documentary claims validated against derived evidence where possible.

The design must decide:

- how a gallery entry links to its materializer evidence and resource
  provenance;
- how paired variants share one semantic fixture while differing only in
  ordinary presentation resources;
- how visual-review artifacts are distinguished from byte-pinned evidence;
- how duplicate, dangling, unverifiable, and misleading claims diagnose; and
- a minimum acceptance matrix for semantic distinction, accessibility,
  supported output target, deterministic reproduction, and review narration.

Acceptance: the catalog cannot become a renderer/configuration layer, and a
reader can trace every displayed design to its exact ordinary resources and
publicly reproducible output.

### GDF-3 — Presentation Package boundary (#343)

Complete #343's design and whole-architecture review before adding a large
collection of designs intended for reuse.  Define the declarative package
manifest, allowed member resource kinds, exact identity/version/content rules,
provenance/license metadata, compatibility/capability declarations, acquisition
and cache behavior, Stage-1/2 use, Stage-3 materialization, fork/repackage
provenance, and offline/disappearance semantics.

The design must explicitly map a gallery entry to a package member without
making the registry a runtime authority.  A Registry/catalog implementation,
publication service, executable plugins, and remote discovery are out of this
phase.

Acceptance: a future gallery design can be packaged or materialized without
rewriting its View/Layout/Theme/Scheme resources or introducing a live registry
edge into its render closure.

### GDF-4 — Visual capability admission decision (#345, conditional)

Before creating any gallery direction that needs a capability unavailable in
the current portable Scene vocabulary, perform #345's design work for that
specific capability family.  Define portable intent, capability profile,
required/optional fidelity, Theme/Color Scheme binding, accessibility,
complexity limits, target behavior, diagnostics, and evidence.

If the first gallery directions fit current primitives and completed paint,
record that decision and defer #345 implementation.  Gradients, images,
clipping, shadows, filters, arbitrary markers, and raw SVG are not admitted by
silence.

Acceptance: every new design treatment is either supported by the current
portable contract or has an approved cross-target capability design before a
gallery asset uses it.

### GDF-5 — Implementation planning and atomic rollout

Only after GDF-1 through GDF-3 are accepted, and GDF-4 is decided for the
chosen directions, publish a separate implementation plan.  Split work into
reviewable slices:

1. Design Summary projection and focused identity/no-authority tests.
2. Gallery catalog schema/tooling and provenance/evidence tests.
3. Package manifest/closure contracts and materialization tests, if #343
   design authorizes a minimal local package implementation.
4. Paired corpus fixtures, public materializer evidence, gallery narration,
   and generated-artifact review.
5. Any approved visual-capability slice, independently from gallery curation.

Each slice must be independently publishable.  A gallery entry never lands
before its source closure and materializer evidence; a package migration never
lands while an existing gallery entry becomes non-materializable.

## Required design reviews

- Review GDF-1 against Specifications 51, 55, and the View → Layout → Scene
  direction.  Reject any summary that becomes an alternate presentation
  authority.
- Review GDF-2 against Specification 58 and the materializer boundary.  Reject
  hand-authored render evidence or metadata-driven rendering.
- Review GDF-3 against package/closure identity, Progressive Authoring,
  materialization, trust, and immutable Context rules.  Reject implicit remote
  resolution and executable authority.
- Review GDF-4 against Scene/renderer separation, target portability, Color
  Scheme authority, accessibility, and deterministic complexity bounds.
- Review the combined rollout for a clean migration from corpus evidence to
  reusable resources, without compatibility shims that duplicate authority.

## Verification strategy

Design acceptance precedes product implementation.  The later implementation
plan must require focused contract tests, full parallel pytest, conformance and
structural gates, public materializer byte checks, generated-SVG diff review,
and installed-wheel smoke.  Gallery-specific checks must prove provenance,
catalog integrity, paired semantic identity, summary derivation, and declared
target/accessibility evidence.

## Explicit deferrals

- Domain/Semantic Packages (#344), unless a chosen gallery fixture demonstrates
  a concrete missing semantic capability.
- Registry service, public discovery, payment, publisher verification, and
  executable plugin architecture.
- A generic diagram framework or the long-term extraction hypothesis in #346.
- New visual capabilities not required by an approved initial gallery direction.

## Completion condition for this plan

This plan is complete when the GDF-1 through GDF-4 design decisions and their
architecture reviews are published, followed by a separately accepted,
atomic implementation plan.  Gallery assets are not created under this plan
alone.

# Implementation Plan: Reusable Design Gallery Foundation

**Status:** Superseded by completed corpus-first rollout
**Date:** 2026-09-23  
**Implements:** [Reusable Design Gallery Foundation Design Plan](reusable-design-gallery-foundation-design-plan-2026-09-23.md), Specifications 55, 58, and 62; UC-29 through UC-31

## Purpose and boundaries

This plan implements the approved reusable-presentation and gallery design in
small, publishable authority changes.  It preserves the existing direction:

```text
authoring ingress -> effective ordinary resources -> Context -> Layout -> Scene -> adapter
                                      \-> Design Summary -> gallery catalogue
```

## #348 correction: evidence before package machinery

The independent #348 tree review found that this plan incorrectly made the
first reusable gallery asset depend on five package-management slices. An
ordinary View, Layout, Theme, or Scheme has its own byte identity and can be
made into a paired corpus slide today; later moving it to a package root does
not change its content. The repository also contains unreproducible legacy
`examples/controller-z/variants/` output, has no public preset example, and
does not yet give the materializer a package-store boundary.

Consequently I-GDF-4 through I-GDF-7 are paused. I-GDF-1 through I-GDF-3 are
not retained as a parallel product path: their Summary and package
implementation are removed or replaced in the correction rollout unless a
revised design proves a current consumer. The next implementation order is:

1. **C-GDF-1 Corpus hygiene and public preset evidence.** Decide legacy
   `variants/` by reproducibility (delete unreproducible artifacts, or replace
   them with declared materializer slides), and add one ordinary
   `presentation-preset` that is committed evidence for an existing Context.
2. **C-GDF-2 Paired ordinary corpus gallery.** Add two distinct portable
   presentation directions over the same Project/Actual schedule as independent
   ordinary Contexts; extend the catalogue successor with provenance, paired
   semantic-identity, target/accessibility, and narration validation. Do not
   require packages, locks, caches, or guided authoring.
3. **C-GDF-3 Release evidence.** Materialize the paired slides, review the
   generated SVG batch, and run the standard release gates.
4. **C-GDF-4 Package decision after demonstrated reuse.** Reopen package work
   only after at least two reusable directions and a concrete acquisition
   consumer exist. First decide whether to specialize the existing profile
   package envelope or deliberately use a distinct presentation-only envelope;
   define materializer/store integration, all diagnostics, and user commands.
   Publish that design correction before new package code.

`PresentationDesignSummary` is deferred: the gallery can validate finite
catalogue assertions directly against effective resource identities, and no
second concrete consumer currently justifies a separate inspection format.

## Correction rollout completion

C-GDF-1 through C-GDF-3 completed with the public Controller Z Executive /
Plan-only pair, reproducible materializer evidence, and GitHub CI. C-GDF-4 is
intentionally deferred: no actual package acquisition consumer exists yet, so
reintroducing package machinery would repeat the premature sequencing corrected
by #348.

The catalogue is documentary only.  A package is a declarative owner of
ordinary presentation resources, never a renderer/plugin/semantic authority.
Project and Actual facts stay outside package roots.  No implementation may
use raw SVG, implicit network access, a `latest` selector, cache paths, or a
registry response as a render input.

The present `authoring-workspace/v0.1` guided `id/version/path` reader is
incompatible with the approved package contract because its mutable local path
is an evaluation edge.  It is removed in the package-aware workspace contract;
there is no compatibility resolver.  Existing corpus fixtures either stay
ordinary explicit resources or migrate atomically with their consuming slice.

## Architecture review before implementation

| Concern | Authoritative owner | Planned implementation boundary | Result |
| --- | --- | --- | --- |
| Design classification | effective ordinary resources | read-only summary projection | no second presentation model |
| Gallery prose/evidence | corpus and materializer | catalogue validator only | no render/configuration authority |
| Reusable presentation resources | package manifest/root | closed package validator | one canonical source tree |
| Selection and pinning | explicit acquisition | package lock writer/verifier | no directory/registry render lookup |
| Guided composition | Authoring Normalizer | locked preset handoff | normalizer still reads all guided syntax |
| Geometry and output | Layout, Scene, renderer | unchanged | packages cannot inject output semantics |
| Local ownership | Stage-3 materializer | atomic ejection + receipt | no live inheritance after ejection |

This review authorizes the slices below.  A newly discovered requirement that
adds a resource kind, package dependency, output capability, or alternate
closure resolver is a design deviation: stop the slice, amend Specification
62 and its review, publish that correction, and only then resume.

## Atomic implementation sequence

### I-GDF-1 — Summary and catalogue inspection boundary

**Files/areas:** `presentation/model/design_summary.py` (new), typed closure
adapters, `docs/gallery/example-gallery.yaml`, catalogue tooling/tests, and
Specification-55/58 examples only if implementation clarifies a published
contract.

Implement a pure `PresentationDesignSummary` projection from an already
resolved effective ordinary resource bundle.  Its values retain source
identities and omit unrepresentable taxonomy values.  Implement catalogue
validation which resolves an entry to corpus/materializer provenance and the
derived summary but returns documentary data only.

**Acceptance:** same semantic fixture with distinct presentation resources
produces distinct summaries; summary/catalogue changes cannot change Context,
Layout, Scene, or bytes; duplicate/dangling/misleading catalogue claims have
stable diagnostics; focused unit tests pass.

### I-GDF-2 — Declarative package contract and source root

**Files/areas:** package schemas, typed package contracts/validator, package
identity utility, `presentation-packages/<namespace>/<id>/` fixtures, package
tests, schema/conformance inventory.

Introduce `presentation-package/v0.1` as a closed manifest.  Validate safe
member paths, permitted kinds only, one member identity/path, exact identities
for all declared bytes, canonical aggregate identity (per Specification 62
section 2), preset membership, license/publisher/compatibility,
and reject symlinks/parent traversal/executable/raw-renderer authority.

**Acceptance:** the package root has exactly one canonical source for each
resource; changing any declared member invalidates content identity; forbidden
members fail before use; no corpus or docs root becomes a package source.

### I-GDF-3 — Explicit local acquisition and lock

**Files/areas:** `presentation/package_acquisition.py` (new), package-lock
schema/contract, CLI `chrona package acquire`, local cache adapter, acquisition
tests.

Acquire from an explicit local root only.  Validate the full package first,
copy verified bytes to a controlled local cache, then atomically write one
provider-neutral `chrona.lock.yaml` containing package, manifest, selected
preset, effective member identities, compatibility and provenance result.

**Acceptance:** missing/corrupt/tampered/untrusted/incompatible/duplicate pins
diagnose without workspace mutation; a lock is complete and deterministic;
acquisition is the sole cache/root lookup; no renderer calls acquisition or
network code.

### I-GDF-4 — Locked guided consumption

**Files/areas:** `authoring-workspace/v0.2` schema/contract, closure resolver,
Authoring Normalizer inputs, guided CLI/tests, migrated guided fixtures.

Replace guided preset `id/version/path` with a compact
`package/id` selector.  Resolve it only through a co-located verified package
lock and cache bytes.  The resolver verifies the pin and hands ordinary
resources to the existing normalizer; it does not inspect package directories
or registry metadata.  Explicit v0.1 workspaces remain separate ordinary
authoring documents; guided v0.1 has no compatibility reader.

**Acceptance:** identical lock/cache bytes create equal normalized resources
and bytes; selector/cache path/catalogue state cannot alter policy; missing
locked bytes emits the declared offline diagnostic; all guided corpus fixtures
migrate in the same publication unit.

### I-GDF-5 — Stage-3 package ejection

**Files/areas:** materialization use case/command, receipt schema, atomic
writer tests.

Eject a verified locked package into a complete local ordinary bundle and
replace the workspace binding atomically.  Receipt `derivedFrom` records the
locked package/preset identities.  Ejection has no remaining lock/cache/package
lookup and proves same-target byte equivalence before it writes.

**Acceptance:** collision or proof failure writes nothing; the resulting
explicit workspace has no package inheritance edge; receipt/provenance is
complete; pre/post materializer bytes agree.

### I-GDF-6 — Paired reusable fixtures and gallery curation

**Files/areas:** eligible package resources, paired corpus Contexts, gallery
catalogue, generated public SVG evidence, narration/accessibility assertions.

Add at least two package directions sharing one Project/Actual schedule while
differing exclusively in View/Layout/Theme/Scheme.  Add their locks/contexts
and catalogue entries only after each is public-materializer reproducible.

**Acceptance:** every entry traces package -> lock -> ordinary resources ->
immutable Context -> public materializer output; paired semantic identity is
proved; output target/accessibility and narration claims validate; generated
SVG changes are reviewed as one batch.

### I-GDF-7 — release acceptance and publication

Run focused tests per slice; at this final boundary run parallel full pytest,
conformance, structural gates, public materializer byte checks, a single
generated-SVG diff review, installed-wheel smoke, and GitHub CI.  Verify remote
`main`, diff, and target commit before each serial push; never force-push.

## Publication and review protocol

Each slice receives: an implementation/architecture review, focused tests,
one serial push, and remote commit/CI confirmation.  I-GDF-6 never lands ahead
of I-GDF-2--5.  I-GDF-7 is the only full release gate; expensive generated SVG
comparison is deliberately batched there unless a slice changes a public
materializer fixture.

## Deferred work

Remote discovery/registry, package dependencies, publisher verification,
semantic packages (#344), generic diagram extraction (#346), and rich visual
capabilities (#345) remain out of scope.  #345 must be designed before any
gallery direction needs unsupported Scene capability.

# Declarative Presentation Packages

**Status:** Proposed  
**Depends on:** [13 Presentation Format](13-presentation-format.md),
[21 Extension Lifecycle](21-extension-lifecycle-successor.md),
[51 Progressive Authoring](51-progressive-authoring.md),
[55 Presentation Design Space](55-presentation-design-space.md),
[58 Example Roles and Evidence](58-example-roles-and-evidence.md), and
[59 Presentation Prefer-ladders](59-presentation-prefer-ladders.md).  
**Owns:** declarative reusable presentation resource bundles, their manifest,
identity, local acquisition/pinning, materialization/fork provenance, and
source-tree boundary.  It does not own a registry service, semantic extension,
renderer plugin, or a new presentation vocabulary.

## 1. Purpose and non-authority

A Presentation Package is a versioned immutable bundle of ordinary Chrona
presentation resources that users may select, acquire, use in guided authoring,
materialize into local ownership, and fork.  It makes a reusable design
portable without making package metadata a second View, Layout, Theme, Scene,
or renderer authority.

The package may contain only already-supported declarative resource kinds:

- `presentation-preset`;
- View;
- Layout Profile;
- Theme;
- Color Scheme; and
- static, immutable assets only when an approved output-capability contract
  admits them.

It cannot introduce a Project/domain field, scheduling rule, semantic registry
entry, Scene primitive, visual capability, arbitrary expression, raw SVG/XML,
CSS, executable code, renderer plugin, network request, or host default.
Specification 59 remains decisive: a package selects existing host-owned
presentation vocabulary; it cannot register a new presentation meaning.

## 1.1 Current implementation status and diagnostics

This specification is a deferred design, not an authorization to introduce a
package resolver before a public reusable corpus direction and a materializer
store boundary exist. The first implementation was paused by the independent
#348 design review; its provisional code must not remain as a parallel public
authoring path.

Before a package implementation resumes, its design must publish these
user-facing operations: `chrona package acquire <candidate>@<release>`,
`chrona package inspect <lock>`, `chrona package propose-update`, and
`chrona package materialize`. It must also reserve stable diagnostics at least
for invalid manifest (`E_PACKAGE_MANIFEST`), escaping or symlink member
(`E_PACKAGE_MEMBER_PATH`/`E_PACKAGE_SYMLINK`), member or aggregate identity
mismatch (`E_PACKAGE_MEMBER_IDENTITY`/`E_PACKAGE_CONTENT_IDENTITY`), duplicate
identity (`E_PACKAGE_IDENTITY_CONFLICT`), incompatible target/version
(`E_PACKAGE_INCOMPATIBLE`), unavailable locked bytes
(`E_PACKAGE_OFFLINE_UNAVAILABLE`), and forbidden authority
(`E_PACKAGE_FORBIDDEN_MEMBER`). Final spellings and semantics require a
separate accepted implementation design.

`profile-v0.2` is a Project semantic-profile package with fields and semantic
constraints; it is not a generic package envelope. A future Presentation
Package may not silently duplicate its identity/lifecycle vocabulary. The
future design must either explicitly specialize common package lifecycle rules
from Specification 21 with a shared identity model, or document the necessary
presentation-only distinction and its migration/interop boundary.

## 2. Package identity and manifest

A release has a stable namespaced package ID, an exact version, and a
content identity over its canonical manifest and all evaluation-relevant member
bytes.  A path locates a member inside a verified release; it is never the
release identity.  An ID/version pair that resolves to different content is an
identity conflict and rejects acquisition.

To avoid a self-referential digest, the canonical manifest contribution is its
decoded JSON value serialized as UTF-8 canonical JSON (sorted keys, compact
separators), with only `package.contentIdentity` omitted.  The package content
identity is SHA-256 over a framed sequence consisting of that contribution and
every evaluation-relevant member's safe relative path plus exact raw bytes,
ordered by path.  Each declared member `contentIdentity` is SHA-256 over its
exact raw bytes and is checked independently before the aggregate package
identity.  YAML formatting therefore affects a member identity as it should;
the manifest's self-declared aggregate digest does not create a circular
definition.  Filesystem metadata, absolute paths, symlink targets, cache
layout, checkout revision, and discovery responses are excluded.

The package manifest is conceptually:

```yaml
format: chrona/presentation-package/v0.1
kind: presentation-package
id: acme/executive-review
package:
  release: 1.2.0
  contentIdentity: sha256:...
  license: CC-BY-4.0
  publisher: {id: acme, displayName: Acme Design}
members:
  presets:
    - {id: executive-light, path: presets/executive-light.yaml, contentIdentity: sha256:...}
  resources:
    - {id: executive-roadmap, kind: view, path: views/executive-roadmap.yaml, contentIdentity: sha256:...}
    - {id: executive-grid, kind: layout-profile, path: layouts/executive-grid.yaml, contentIdentity: sha256:...}
    - {id: executive-light, kind: theme, path: themes/executive-light.yaml, contentIdentity: sha256:...}
    - {id: daylight, kind: color-scheme, path: schemes/daylight.yaml, contentIdentity: sha256:...}
compatibility:
  chrona: ">=0.1.0a0 <0.2.0"
  targets: [chrona-output/svg/v0.5]
provenance: {}
```

The final schema must use closed typed members, safe package-relative addresses,
and exact content identity for every evaluation-relevant member.  It must carry
machine-readable publisher, license, compatibility, deprecation/replacement,
and optional `derivedFrom` provenance.  Human-readable discovery classification
is catalog metadata, not a runtime input.  A preset maps to its members using
the existing ordinary resource identities; it cannot embed another generic
override layer.

Package-to-package dependencies are excluded from the first package profile.
They add a second resolver and lifecycle surface without a demonstrated
reusable-design use case.  A later profile may admit them only under
Specification 21's exact, acyclic, deterministic dependency rules.

### 2.1 Discovery classification and candidate result

A package may declare a finite Design Space classification for discovery, such
as intended audience, supported surface, declared composition family, and
appearance/target suitability.  This classification is metadata: it must reuse
the vocabulary of Specification 55, cannot name coordinates or renderer syntax,
and cannot change the package's effective resources.

A future local, private, or public registry receives a discovery query and
returns **candidates**, never an active package.  A candidate contains at least
the package ID, exact available version, manifest content identity/reference,
publisher/license/trust status, compatible Chrona/target profile, declared
classification, and the stable IDs of offered presets.  A result may be sorted
or filtered for presentation, but it cannot return a mutable default, `latest`,
or a resource closure selected by name alone.

Selection of a candidate always proceeds through the explicit acquisition step
in section 4.  The registry response is not recorded as render input; the
verified acquired manifest and lock are.  A private catalogue and a local
directory use the same candidate/result and acquisition semantics, differing
only in their configured trusted source.

## 3. Canonical source-tree topology

The canonical package source is distinct from project-owned corpus and from
documentation:

```text
presentation-packages/
  <publisher-namespace>/<package-id>/
    package.yaml
    presets/
    views/
    layouts/
    themes/
    schemes/
    assets/                  # only approved static asset kinds
    examples/                # optional package-owned inputs; no public SVG evidence
```

`examples/<project>/` remains the owner of Project/Actual facts, immutable
Contexts, corpus manifest, and generated materializer evidence.  It may consume
one acquired package through immutable references, but it must not copy the
package's View/Layout/Theme/Scheme sources.  `docs/gallery/` references corpus
slides and package provenance only.  It owns neither package source nor
generated rendering evidence.  `src/chrona/resources/` and `conformance/`
remain separate product/runtime and normative-fixture roots.

Member paths are safe relative addresses below the package root.  Symlinks,
parent traversal, ambient repository-root lookup, and a mutable checkout path
are invalid acquisition or resolution mechanisms.  A release archive/cache may
choose its storage layout, but that layout is not part of package identity.

## 4. Selection, acquisition, and offline use

Human selection is intentionally shorter than a closure pin:

```yaml
presentation:
  mode: guided
  binding:
    preset: {package: acme/executive-review, id: executive-light}
```

This selector is authoring convenience only.  Before rendering, an explicit
acquisition operation resolves it once to a verified package release and writes
an immutable package lock.  The lock records package ID/version/content
identity, verified manifest reference, selected preset identity/content
identity, resolved ordinary resource identities, compatibility result, and
provenance/trust result.  It becomes a declared guided-closure input; the cache
location merely supplies its already verified bytes.

The first implementation may acquire from a local package root, but the stored
lock is provider-neutral and must have the same shape required by future private
or registry acquisition.  A local directory is an acquisition input, not a
long-lived render reference.  Render and materialization never search a
directory, contact a registry, select `latest`, or silently upgrade a release.

Missing local bytes for a valid lock diagnose offline unavailability.  Missing,
corrupt, untrusted, incompatible, duplicate-identity, or unsupported packages
diagnose before normalization.  They leave the preceding workspace/closure
unchanged.  An update is an explicit proposal producing a different reviewed
lock; deprecation is information, never an implicit migration.

## 4.1 Publication quality gate

Before a package is offered as a discoverable candidate, its publisher validates
the manifest, every declared member identity, license/provenance, supported
Chrona and target profiles, and the absence of forbidden executable/raw
members.  It must be exercised against representative semantic fixtures
appropriate to its declared design direction: a small schedule, dense rows,
long labels/date range, groups, Plan/Actual comparison, and any declared
accessibility/target boundary.  The package may publish derived preview
artifacts for inspection, but a preview cannot establish correctness.

The normative evidence is deterministic resource/closure validation and public
materialization through the ordinary render path.  A package that is only
visually attractive on one hand-authored SVG is not publishable.  A later
registry service may verify and expose these results, but it must not replace
the package's exact identity or re-render a package with unstated host policy.

## 5. Guided use and evaluation closure

The package resolver verifies the locked manifest and members, then hands the
already-acquired ordinary resources to the existing Authoring Normalizer.  The
normalizer remains the sole reader of guided syntax and does not search package
trees, inspect registry metadata, or select a fallback.  Its output remains the
ordinary Project/Actual/View/Theme/Scheme/Layout bundle.

An immutable guided evaluation records the workspace, lock, package manifest,
selected preset, effective ordinary resources, target, environment, and
normalizer identity.  The package selector, package cache address, gallery
metadata, and registry response are not rendering policy.  Equal immutable
inputs must produce the same normalized bundle and output.

## 6. Materialization, fork, and migration

Stage 3 materialization is the existing one-way transition.  It writes a
complete local ordinary View/Theme/Scheme/Layout/Render Context bundle and a
receipt, verifies byte-equivalent output in the same target/environment, and
removes every live package/lock inheritance edge from the explicit workspace.
The receipt records the selected package/preset pin as `derivedFrom` provenance;
it cannot use it as a fallback.

A fork begins only after materialization.  Publishing it creates a new package
ID/version/content identity and optional `derivedFrom` chain.  It does not
mutate a source release or rely on package overlay semantics.  License and
publisher/provenance validity are acquisition/publication gates.

Existing corpus fixtures migrate atomically: a fixture either remains ordinary
explicit source or consumes one complete verified package.  No compatibility
resolver keeps legacy guided `id/version/path` spelling alongside the approved
package-aware contract, and no fixture may become non-materializable during the
migration.

## 7. Gallery relationship

A gallery entry points to a corpus slide, its materializer evidence, and the
derived Design Space summary.  It may state package/preset provenance, but it
does not resolve package members.  Gallery curation remains documentary; the
package manifest and lock establish reusable resource identity.

The first reusable gallery directions must be paired corpus variants using the
same semantic Project/schedule fixture and distinct package presentation
resources.  They must be materializable independently, even if their package
is unavailable after Stage 3 ejection.

## 8. Explicit deferrals

This specification does not implement or require a public registry, remote
fetch, publisher verification service, payment, package dependencies,
executable plugins, dynamic presentation registry, Domain Package, or a visual
capability beyond the current closed Scene contract.  #345 is required before a
package claims any unavailable visual treatment.

## 9. Required implementation evidence

Implementation requires schemas and fixtures for a valid local package,
malformed/escaping member address, missing/tampered member, identity conflict,
unsupported resource kind/capability, incompatible target, offline-missing
lock bytes, attempted implicit update, forbidden executable/raw SVG content,
and a clean Stage-3 ejection/fork provenance path.  It also requires paired
corpus materializer evidence, gallery catalog integrity, full conformance and
structural gates, full pytest, generated-SVG diff review, and wheel smoke.
These requirements trace to UC-29 through UC-31 in the Use Case Catalog.

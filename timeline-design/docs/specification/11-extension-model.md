# Extension Model

**Status:** Draft
**Depends on:** [02 Domain Model](02-domain-model.md), [04 Scheduling Model](04-scheduling-model.md), [05 Project Format](05-project-format.md), [07 Style and Theme](07-style-and-theme.md), [10 Command Model](10-command-model.md)
**Owns:** declarative domain packages, custom profiles and typed fields, profile inheritance and fallback, derived-field boundaries, extension validation and compatibility, and the separation of semantic extensions from code plugins.

## 1. Purpose

Chrona remains small by allowing domain vocabulary to be added without expanding the Core primitive set for every industry or team. An extension can describe concepts such as `gate`, `EVT`, `qualification`, `component`, or `customer-review` while retaining the known semantics of a TemporalPoint, TemporalSpan, Entity, Relation, or Annotation.

An extension is not permission to turn Chrona into a generic graph database, arbitrary programmable scheduler, workflow engine, or renderer-authoritative canvas.

```text
Semantic extension  → declarative package + schema
Presentation tokens → Style / Theme declarations
Rendering extension → host-installed code plugin
```

Only the first category contributes to canonical Project semantics.

## 2. Invariants

- Every semantic profile MUST ultimately extend exactly one supported Core primitive through a declared, acyclic inheritance chain.
- Extension fields MUST be declared, serializable, type-checkable, and namespaced by their owning profile or package.
- Project data MUST NOT execute arbitrary host-language code, access the network/filesystem, inspect local runtime state, or call a renderer while being validated or evaluated.
- An extension MUST NOT redefine Core temporal types, half-open span semantics, endpoint dependency semantics, scheduling authority, or the distinction between planned and Actual state.
- Unknown profiles MAY degrade only through a declared and resolvable supported ancestor; otherwise they are diagnosed rather than guessed.
- A semantic extension MUST remain usable without a particular View, Theme, Scene, renderer, or code plugin.
- Extension package selection and version resolution MUST be explicit and reproducible for a Project revision.

## 3. Extension package model

A **domain package** is a versioned, declarative collection of profiles, field schemas, relation constraints, derived-field declarations, and optional examples. Its concrete file layout and acquisition mechanism are deferred, but a resolved package has the following conceptual manifest.

For v0.1, its persisted manifest uses the common package identity below. `contentIdentity`
is the SHA-256 identity of the resolved manifest payload; retrieval may remain
implementation-defined, but a loaded manifest is canonical and schema-valid:

```yaml
version: chrona/profile/v0.1
packageId: semiconductor-development
contentIdentity: sha256:<64-hex>
requires: {projectFormat: timeline/v0.1}
profiles:
  EVT: {extends: milestone}
```

Each profile has an `extends` parent, declared fields, and optional declarative
constraints. A standalone type list is not a package and cannot establish extension
compatibility.

| Field | Meaning |
|---|---|
| `packageId` | Stable package namespace, for example `semiconductor` |
| `version` | Declared package version compatible with the Project format |
| `contentIdentity` | Content hash or equivalent immutable identity of the resolved declaration |
| `requires` | Explicit Core/format and package compatibility requirements |
| `profiles` | Declared profiles, inheritance, fields, constraints, and allowed relations |
| `derivedFields` | Typed, declarative derived-field declarations |
| `migrations` | Explicit supported migrations between package versions, if supplied |

A Project references `{packageId, path, revision, contentIdentity}`, not an unpinned
“latest” schema. Package and profile inheritance graphs are resolved before Project
validation; cycles, missing parents, and incompatible Project format are diagnostics.

## 4. Profiles and inheritance

### 4.1 Profile declaration

A profile declaration contains at least a globally unique profile ID, one `extends` parent, a field schema, and any declarative constraints. It MAY additionally declare permitted child profiles, allowed relation profiles, and derived fields.

```text
TemporalPoint
└── semiconductor.gate
    ├── semiconductor.evt
    ├── semiconductor.dvt
    └── semiconductor.pvt
```

Profile inheritance is single-parent. This keeps the semantic base, field ownership, constraint order, and unknown-profile fallback unambiguous. Shared vocabulary belongs in a common parent profile or a typed field schema, not in multiple semantic parents.

### 4.2 Valid inheritance targets

The root of every profile chain is one of the known Core primitives:

```text
TemporalPoint
TemporalSpan
Entity
Relation
Annotation
```

A package may specialize a standard profile such as `task`, `phase`, `milestone`, or `dependency` only if the resulting chain still reaches its Core primitive. It may not use inheritance to change a Point into a Span, turn a decorative arrow into a dependency, or add scheduling authority to an annotation.

### 4.3 Resolution and fallback

Consumers resolve the full declared inheritance chain before applying fields or constraints. Field and constraint conflicts are invalid unless the child explicitly supplies an allowed deterministic override defined by its schema rules.

A consumer that does not understand a leaf profile MAY present or preserve it through the nearest known ancestor only when it can verify the chain and retain unknown extension data losslessly. It MUST:

- preserve the original profile ID and uninterpreted data;
- avoid evaluating unknown constraints, derived fields, or scheduling behavior;
- label the fallback in diagnostics or inspection metadata; and
- reject mutation that requires understanding the unknown specialization.

Fallback does not grant scheduling or validation conformance for an unknown profile.

## 5. Typed fields and declarative constraints

### 5.1 Field schemas

Extension fields are owned by a profile and have declared type, presence, cardinality, defaulting rule, validation constraints, and reference target type where applicable. Initial reusable types include the Core field types:

```text
string, number, boolean, enum, tags,
Date, DateTime, temporal amount,
object reference, object reference[]
```

Additional types MAY be introduced only if they have deterministic serialization, equality, validation, and Git-reviewable normalization rules. Opaque blobs, executable payloads, mutable object references, and renderer-specific state are not semantic field types.

Defaults must be explicit in the resolved schema. A default that depends on current time, current branch, local locale, host process, network data, or a renderer is invalid.

### 5.2 Constraints

Constraints express structural and semantic restrictions declaratively: required fields, type/range/enum membership, reference target profile, allowed relation profile, and permitted placement mode are representative examples.

Constraints may reject invalid source data but may not silently rewrite it. Complex graph or scheduling analysis remains in the appropriate Core engine, whose results may be exposed as derived fields rather than recreated inside package constraints.

## 6. Derived fields and expressions

A derived field declares its output type, explicit source fields or engine-produced inputs, expression, unknown-value behavior, and evaluation version. It is computed state and MUST NOT be serialized as an independently authoritative Project fact unless a later specification explicitly makes it an observed input.

The initial allowed expression model is a terminating, side-effect-free declarative language over declared typed inputs. It may support field access, literals, comparisons, boolean operations, arithmetic on compatible values, enum/tag membership, and explicit conditional selection. It MUST NOT permit:

- arbitrary host-language code, imports, reflection, loops, recursion, mutation, or dynamic evaluation;
- network, filesystem, process, clock, random, environment, or renderer access;
- unconstrained traversal of the Project graph; or
- defining new temporal arithmetic or scheduling solvers.

Derived fields may consume a named result already produced by a Core engine—for example a resolved planned placement, slack, or a comparison variance category—but cannot alter that result. Cycles among derived fields are invalid and diagnosed.

## 7. Relations, entities, and scheduling boundary

Packages may define custom Entity and Relation profiles with typed fields and permitted endpoint/source kinds. A custom relation is not automatically a dependency.

Only a Relation profile declared compatible with the Core dependency semantics may participate in Scheduling Engine constraint construction. Such a profile uses the same endpoint, lag, calendar, authority, cycle, and diagnostic rules as the Core; it cannot supply arbitrary solver code, change a fixed target, or make Actual observations scheduling inputs.

Extensions cannot add resource capacity, cost optimization, timesheets, ticket workflows, portfolios, or a generic graph-operation language merely by adding fields. A feature that needs a new Core primitive, temporal domain, or scheduling rule requires Core specification review and normally an ADR.

## 8. Presentation and code-plugin boundary

Semantic packages may declare namespaced visual-role vocabulary and token requirements that Style and Theme can resolve. They must not embed literal renderer geometry, SVG markup, tldraw records, or executable drawing behavior in Project data.

Renderer integrations, renderer-private composite drawing behavior, importers, and
editor behaviors are code plugins installed and trusted by the host, not semantic
package data. A code plugin:

- declares its compatible package/API versions and required host capabilities;
- receives only the completed, typed inputs appropriate to its adapter boundary;
- cannot mutate canonical Project state except by submitting ordinary Commands; and
- must report capability or fidelity loss rather than silently changing semantics.

Plugin acquisition, sandboxing, trust, and approval policy are deferred to Application Architecture. Installation of a plugin does not itself grant mutation authority or change the meaning of a Project.

A plugin MUST NOT introduce a new standard Scene primitive by private convention. New
standard primitives require the versioned Scene specification change defined in
[08 Scene and Rendering](08-scene-and-rendering.md). A renderer-private composite may
only implement already-defined Scene semantics and must not be required in canonical
Project data.

## 9. Compatibility, migration, and diagnostics

Package versions are independent of the Project-format version but declare compatibility with it. A breaking change to field interpretation, inheritance, constraint meaning, or derived expression behavior requires a new package version and an explicit migration or a validation failure.

Migration is an explicit Command-governed transformation from one resolved package identity to another. It MUST report the normalized canonical changes, preserve stable semantic IDs where possible, and never execute untrusted migration code from project data.

At minimum, validators diagnose:

- unresolved package identity or incompatible version;
- unknown or cyclic profile inheritance;
- duplicate namespaced IDs or ambiguous field ownership;
- unknown field, invalid type, invalid reference, or forbidden default;
- unsupported expression operation, derived-field cycle, or unavailable engine input;
- relation/scheduling boundary violation; and
- lossless-fallback impossibility or renderer plugin capability loss.

## 10. Command integration

The Command Engine uses the resolved extension schema to validate profile assignment and typed-field commands. Extension packages may contribute declarative command descriptors only where those descriptors reduce to the standard command families and validated typed payloads.

An extension cannot register an opaque command handler, bypass base-revision checks, mutate derived state, or introduce a hidden write channel. New command semantics that cannot be represented by the standard families require a Command Model and Extension Model change before implementation.

## 11. Out of scope

This document does not define:

- extension package file syntax, registry protocol, dependency solver, or installation UX;
- arbitrary code plugins, their sandbox implementation, or their permission UI;
- new Core primitives, DateTime/DST scheduling, or resource/cost/workflow systems;
- a user-defined general-purpose programming language; or
- View/Style/Theme/Scene serialization or a renderer-specific extension API.

## 12. Boundary to quality and implementation

[12 Quality and Invariants](12-quality-and-invariants.md) defines the cross-system properties extensions must preserve: meaningful Git diffs, determinism, semantic isolation, renderer independence, and safe expressions. Implementations may add package tooling only after schemas, canonical examples, diagnostics, and compatibility tests make these rules executable.

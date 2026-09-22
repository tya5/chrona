# Issue 222 Progressive Authoring Architecture Integration Review

**Review scope:** the approved Issue 222 design in
`issue-222-progressive-authoring-design-2026-09-22.md` and its normative successor,
[51 Progressive Authoring](../../specification/51-progressive-authoring.md).
**Result:** Accepted as an implementation entry point. No runtime implementation is
included in this review.

## Review method

The review followed the ownership and dependency direction in Specifications 05–10,
12, 13, and 21. It checked each new authoring concern against the existing canonical
semantic, presentation, closure, command, package, and derived-state owners. A design
is accepted only where it identifies one durable owner, preserves the ordinary typed
evaluation path, and gives failure and provenance behavior before implementation.

## Integration findings

| Boundary | Finding | Decision |
| --- | --- | --- |
| Project and Actual authority | Compact task and observation spellings could otherwise become a parallel semantic format. | The workspace is syntax only; it normalizes to Project v0.5 and Actual Set v0.2, whose validation and scheduling remain authoritative. |
| Existing explicit/draft route | Treating loose-resource `chrona render` as a preset workflow would create hidden defaults. | It remains an explicit Draft route. Guided Draft is separately labelled and creates no snapshot or hidden files. |
| Immutable closure | A preset name, registry tip, host font, or editor state would make output irreproducible. | Guided immutable closure records exact workspace, package, binding, normalizer, effective resources, target, and environment identities. |
| Package lifecycle | A preset could accidentally behave as executable plugin or profile inheritance. | It is a declarative verified package member governed by Specification 21: exact identity, trust, compatibility, explicit upgrade, and no code. |
| Presentation ownership | Stage-2 convenience could leak scheduling or geometry controls into source. | The override vocabulary is closed to View-local intent and admitted scheme selection. Layout, fonts, routes, coordinates, target, and semantic state reject. |
| Command atomicity | Ejecting a preset touches multiple resources and cannot fit an accidental sequential file edit. | A successor Command Engine transaction names all canonical files, validates the normalized candidate and output proof, then writes all-or-nothing with one CAS base. |
| Layout, Scene, renderer | A guided implementation could allow raw compact fields to reach geometry or serialization. | Only normalized typed closure enters the existing pipeline. Scene and renderer retain no workspace state and cannot become a mutation path. |
| Stage 3 ownership | Retaining an inherited edge after materialization would split truth between local files and preset. | Materialization is one-way. The receipt is non-rendered provenance; output thereafter uses only explicit resources. |
| Extension / Issue 148 | A terse front end might duplicate normalization or materialization policy. | It is constrained to parsing into the workspace schema. It cannot own a model, resolver, override grammar, or command behavior. |

## Architecture conformance

The resulting flow preserves the Application Architecture direction:

```text
CLI / GUI / AI / automation -> Command Engine -> Revision Store
                                      |
workspace + verified preset -> Authoring Normalizer -> typed closure
                                      |
Project -> Scheduler -> View -> Style/Theme -> Layout -> Scene -> Renderer
```

The normalizer is an ingress adapter, not a new runtime layer after View or Layout.
It is therefore prohibited from choosing geometry, invoking a renderer, altering a
schedule, accepting undeclared defaults, or persisting a derived result. Its output is
the same typed closure contract that existing explicit resources use. This preserves
the Presentation Format requirement that every reproducible input has an exact identity,
and the Command Model rule that no client persists Scene/SVG/canvas state.

The only designed multi-resource transaction is materialization. Its command target is
an `authoring-workspace` aggregate whose base revision covers the named workspace and
generated resource destinations. This is a deliberate successor extension to the
single-target v0.1 command serialization, not an exception hidden inside a client.
Implementation must version its request/result contract and revise the Command Model's
transaction wording before accepting it. Until then, the current command registry does
not claim to support these commands.

## Determinism, failure, and migration review

Preset selection and upgrade are explicit identity changes; normal evaluation never
follows `latest`, a branch, a directory, host locale, host font, or renderer fallback.
For equal immutable ingress, target, and environment, both guided rendering and the
Stage-2-to-3 output proof must be byte-equivalent. Missing/untrusted/incompatible
packages, unknown override members, incompatible scheme selections, stale bases,
destination collisions, incomplete closure, and failed equivalence proof leave durable
state unchanged and return stable diagnostics.

There is intentionally no legacy compatibility parser or implicit conversion. Existing
explicit projects remain valid Stage 3 closures. A user who chooses materialization
receives a reviewable explicit diff and receipt; no reverse inheritance or silent
migration exists. This avoids a source-of-truth split and keeps Git review, undo/redo,
and failure recovery ordinary Revision Store operations.

## Required implementation gates

The design is complete; the following are implementation gates, not unresolved design
questions:

1. Add closed, versioned schemas and canonical examples for workspace, preset, binding,
   receipt, and successor commands, with explicit owner updates to Specifications 10 and
   13.
2. Implement and test the normalizer/preset resolver as the sole guided ingress, with
   malformed, missing, untrusted, incompatible, and illegal-override diagnostics.
3. Implement Command Engine aggregate CAS and materialization, proving no partial
   writes, correct stale/collision handling, and ordinary undo/redo revisions.
4. Prove immutable provenance and deterministic Stage-1/Stage-2 renders, then prove
   byte-equivalent Stage-2-to-3 output and explicit-route bypass.
5. Run public materializer coverage, generated-artifact diff review, focused tests, and
   the full suite before any product reachability claim.

These gates align UC-22–UC-28 with the catalog without implying that their current
status is implemented. The proposed specification and review close Issue 222's design
phase and provide the only allowed basis for a later implementation plan.

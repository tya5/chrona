# Issue 338 Presentation Design Space Architecture Review

**Review scope:** [55 Presentation Design Space](../../specification/55-presentation-design-space.md),
its design plan, and the published progressive-authoring contracts and normalizer.
**Result:** Accepted as the design basis for a later implementation plan.  No product
schema or run-time behavior is changed by this review.

## Method

The review traced every proposed selectable dimension from its authored owner to
its derived consumers: Project/Actual -> View -> Layout -> Scene -> renderer.
It also traced each Stage-2 member through `authoring-workspace/v0.1`, the
structural normalizer operation, closure provenance, and Stage-3 materialization.
An item was accepted only if it has one owner, a finite validation boundary, and
no reverse dependency from a downstream derived layer.

## Findings and decisions

| Concern | Evidence | Decision |
| --- | --- | --- |
| A flat preset map would duplicate resources and invite renderer configuration. | The preset already pins View, Theme, Scheme, and Layout Profile references; the normalizer returns those ordinary contracts. | A preset remains a named point expressed by ordinary resources.  A derived summary is inspection-only. |
| `density`, label behavior, and adaptive axis could be mistaken for coordinates. | View has visibility intent; Layout owns measurement, fitting, placement, and routing. | Keep only consumed intent/profile choices authored. Coordinates, metrics, collision decisions, and routes remain derived. |
| Visual grammar can blur View, Theme, Scene, and adapter responsibility. | View/semantic presentation select semantic forms; Theme completes appearance; Scene completes renderer-neutral forms; adapters serialize them. | Do not add an independent grammar bag.  A future variant must extend its owning versioned contract and complete before Scene. |
| Guided convenience can alter semantic identity. | The current binding grammar admits only window, grouping, visibility, logical annotations, and preset-compatible scheme selection. | The matrix preserves this set.  No new guided capability is authorized by #338 alone. |
| A guided field might be accepted by schema but fail after normalization. | The normalizer reparses the effective View/Scheme through the existing contracts. | Guided operations are valid only when the complete resulting ordinary resource validates; rejection has no fallback. |
| Materialization could leave both local and preset authority. | The materializer emits complete effective resources, receipt identities, and a byte-equivalence proof. | Stage 3 remains one-way and explicit mode has no preset edge. |
| Explicit projects could be forced into a new facade for vocabulary inspection. | UC-28 and Specification 51 require the normal explicit closure route. | Any Design Summary for explicit resources is derived locally; it never invokes guided normalization or migration. |
| A new schema might be premature. | Current View v0.8, Layout Profile v0.3, Theme v0.3, Scheme, and preset references express all current taxonomy values. | No schema successor is warranted now.  Add one only for an independently selectable, owner-defined intent that cannot be represented without duplication. |

## Cross-specification conformance

The design preserves the directional architecture:

```text
authoring facade -> ordinary typed resources -> View -> Layout -> Scene -> adapter
                                           Theme/Scheme -> Scene paint
```

It does not grant the facade authority over Project, Actual, Temporal,
Scheduling, the semantic dependency graph, Layout geometry, or renderer
capabilities.  It also does not move Theme lookup into adapters: completed Scene
paint remains the renderer input.  This conforms with the existing progressive
authoring, intent-layout, closure-integrity, and completed-paint specifications.

The current normalizer's operations are consistent with the design's precedence
law: window and grouping replace their named View values, visibility merges only
its declared members, annotations append after identity validation, and Scheme
selection is limited to preset declarations.  There is no generic merge and no
partial explicit mode.  The existing guided provenance carries the workspace,
preset, binding, normalizer, and effective closure identities required by the
design; a future Design Summary must reference rather than duplicate them.

## UC-22--UC-28 review

The taxonomy makes UC-22 preset-first because a beginner supplies a preset name,
not dimension values.  It makes UC-24 and UC-25 reviewable because every guided
operation has an owner and no derived geometry.  It preserves UC-26 provenance
by retaining the existing closure records, UC-27 atomic ejection by retaining a
complete effective bundle and byte proof, and UC-28 by keeping the explicit
route independent.  UC-23 remains semantic-only: a task or Actual update is not
a hidden presentation selection.

## Required implementation gates

1. Decide the first concrete consumer of the taxonomy before adding any code;
   do not create a summary, schema version, or UI control without that use case.
2. If a guided capability is proposed, amend the matrix first with its owner,
   finite vocabulary, compatibility predicate, merge law, provenance, stable
   diagnostic, and identity-preservation fixtures.
3. Add paired fixtures using one Project/schedule with at least two preset points,
   then prove different effective presentation closures without semantic changes.
4. Cover allowed and rejected guided boundary values, deterministic normalization,
   complete materialization, Stage-2-to-3 byte equivalence, and explicit-route
   bypass.  Run public materializer checks and the full suite before publication.

The design phase is therefore complete.  The next phase is an implementation
plan only after a bounded consumer has been selected; it is not authorization to
broaden guided authoring speculatively.

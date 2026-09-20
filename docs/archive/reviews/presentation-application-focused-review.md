# Presentation and Application Focused Review

**Status:** Review complete  
**Reviewed artifacts:** `07`–`12`  
**Result:** Proposed promotion approved

## 1. Purpose

This review determines whether the Presentation and Application specifications are
coherent enough for focused implementation planning. It evaluates responsibility
boundaries, dependency direction, source-of-truth authority, and cross-layer contracts.
It does not approve a renderer, GUI framework, persistence syntax, or implementation.

## 2. Review criteria

The reviewed documents must:

1. preserve Project and scheduling semantics independently of presentation;
2. assign each concern to one authoritative layer;
3. connect View, Style, Theme, Scene, Application, Command, and Extension without
   reverse dependency from renderer to semantic source;
4. preserve stable identity and reproducible explicit inputs through interactive update;
5. keep plan, Snapshot, Actual, dependencies, explanatory arrows, and annotations
   distinct; and
6. leave implementation details as explicit deferred work rather than implicit behavior.

## 3. Reviewed interfaces

| Boundary | Conclusion |
|---|---|
| View → Style / Theme | View selects semantic content and emphasis. Style maps it to roles; Theme supplies concrete token values selected by Render Context. View cannot override token values. |
| Style / Theme → Scene | Scene receives resolved roles and tokens, then assigns renderer-neutral geometry without re-deciding meaning. |
| Scene → interactive adapter | A completed Scene initializes an adapter. `SceneDelta` provides atomic, identity-preserving incremental reconciliation by `sceneId`. |
| Application → SceneDelta | Application computes the impact set and evaluation lifecycle; Scene/Rendering owns the delta operation contract. Global replacement requires an explicit reason. |
| GUI / CLI / AI → Command | All clients submit revision-bound Commands. Preview state is transient; accepted changes create a new canonical revision and derived output is rebuilt. |
| Actual → View / schedule | Actual may be resolved or explicitly unmatched. It is diagnosed and reviewable, never title-matched or used to implicitly reschedule planned work. |
| Extension → Scene / renderer | Semantic packages remain declarative. Plugins may implement renderer-private composites but cannot introduce a standard Scene primitive or canonical mutation path by private convention. |
| Quality → all layers | Quality cross-cuts all documents and constrains them; it is not a downstream dependency that creates a cycle. |

## 4. Resolved findings

The review found and resolved the following cross-document issues before promotion:

- concrete Theme token overrides were removed from View responsibility;
- the `SceneDelta` adapter contract was moved to Scene and Rendering, while Application
  retains impact-set calculation and delivery lifecycle;
- the Quality document's dependency cycle was replaced by a cross-cutting relationship;
- unmatched Actual observations gained a diagnostic-preserving Command path; and
- extension plugins were prevented from introducing standard Scene primitives without a
  versioned Scene specification change.

## 5. Intentionally deferred work

The following work remains necessary before implementation claims conformance, but does
not leave current semantic ownership ambiguous:

- YAML/JSON schemas and canonical persistence forms for View, Style, Theme, Render
  Context, Snapshot, Actual, and Command envelopes;
- selector and derived-expression grammar;
- Scene layout-engine, text-shaping, transport, GUI, and renderer-library choices;
- command authorization, approval UX, and external package acquisition; and
- deterministic examples and conformance fixtures for projection, `SceneDelta`, command
  transactions, extensions, Snapshot, and Actual.

## 6. Promotion result

`07 Style and Theme`, `08 Scene and Rendering`, `09 Application Architecture`,
`10 Command Model`, `11 Extension Model`, and the cross-layer expansion of
`12 Quality and Invariants` are promoted to **Proposed**.

Proposed means their ownership and normative boundaries are coherent and ready for
focused review against schemas, examples, and implementation plans. It does not mean
the deferred persistence formats or implementations are complete.

## 7. Next design gate

The next gate is a serialization and fixture pack. It must define and test the explicit
inputs used by these specifications before a GUI or renderer implementation is allowed
to establish behavior by convention.

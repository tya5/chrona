# Runtime and Reactivity Design

**Status:** Proposed  
**Owns:** Runtime Coordinator request/result contracts, evaluation identity, cache keys,
impact-set derivation, stale-result handling, and SceneDelta lifecycle.

## 1. Evaluation contract

An evaluation request names one Render Context revision and optional requested artifact.
The coordinator resolves all Context references before work begins and returns an
immutable result containing `evaluationId`, input manifest, Scene or artifact,
diagnostics, and cache provenance. An evaluation never reads a current branch, local
clock, installed-font default, or unrelated Context.

`evaluationId` is a hash of normalized Project/Snapshot/Actual/View/Style/Theme/Scene
profile revisions plus viewport, target capabilities, layout-metrics revision, locale,
and evaluation date when used. Equal identities are observationally equivalent.

## 2. Cache and impact set

The cache is an optimization indexed by `evaluationId`; it never hides diagnostics.
For an accepted Command, the coordinator computes an **impact set** from changed stable
IDs, changed owning fields, schedule dependency closure, View selection/group/order,
Style rules, Theme token references, Scene profile, and viewport.

| Change | Minimum impact | Permitted global reason |
|---|---|---|
| Actual observation | aligned comparison facets and their Scene nodes | none by default |
| local Project field | affected object plus declared dependency/View closure | dependency closure only |
| Theme token | nodes referencing that token | only layout-metric token change |
| View, viewport, scale, Scene profile | declared projection/layout domain | `viewport-reflow` or `scale-change` |

The previous and next completed Scenes are compared by `sceneId`. The coordinator emits
`upsert`, `remove`, `reorder`, and `tokenUpdate`; `replaceScope: scene` is rejected
unless the input change has a declared global reason.

## 3. Concurrency and transient state

Interactive preview, hover, selection, and drag state are client-local. A gesture creates
a Command proposal bound to the revision it inspected. On acceptance, the client applies
the matching SceneDelta; on rejection, it removes only the affected preview.

The coordinator tags all work with `evaluationId`. A completed result whose identity is
older than the latest requested identity is discarded or retained only as a cache entry;
it MUST NOT overwrite the newer Scene. Concurrent canonical writes use Command
base-revision conflict behavior; no hidden last-writer-wins is permitted.

## 4. Required diagnostics

`RUNTIME-UNRESOLVED-INPUT`, `RUNTIME-STALE-RESULT`, `RUNTIME-CACHE-PROVENANCE`, and
`PRES-SCENE-DELTA-SCOPE` are stable diagnostic categories. Diagnostics identify their
owning reference and revision.

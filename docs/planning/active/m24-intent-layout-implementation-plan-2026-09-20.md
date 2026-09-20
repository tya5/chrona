# M24 Intent-Oriented Layout Implementation Plan — 2026-09-20

**Status:** Approved implementation plan; runtime changes not started.  
**Design authority:** Specification 33, ADR-0023, and the M24 design review.  
**Delivery rule:** Each slice is tested, committed, and published to `main` before the
next slice starts. An implementation-discovered semantic gap returns to design first.

## 1. Target state

One runtime path resolves immutable Project, View, Theme, Layout Profile v0.2, optional
Actual/Summary/Detail, and Render Context v0.4 inputs into measured layout, Layout
Manifest, Scene, and SVG. The v0.1 Layout Profile, bundled Presentation Preset/Settings
layout authority, and compatibility branches are absent from the reachable product.

## 2. Module boundaries

| Module | Responsibility | Must not do |
|---|---|---|
| `presentation/layout/model.py` | immutable sizes, distances, nodes, measurements, bounds, manifest records | load resources or render |
| `presentation/layout/profile.py` | schema/semantic validation, canonical hash, inheritance, stable-ID overrides, Theme number-token resolution | calculate Project facts or geometry |
| `presentation/layout/engine.py` | measure/arrange tree, grid/flow/distribution/alignment, safe overflow | read YAML, branch on profile IDs, invent metrics |
| `presentation/layout/relative.py` | overlay guides, barriers, dependency graph, anchors and cycle diagnostics | solve arbitrary equations |
| `presentation/model/closure.py` | resolve v0.4 Context and immutable Theme/Layout refs | keep Preset fallback |
| `presentation/scene/*` | map resolved slots and measured sources to source-linked Scene primitives | reinterpret profile or supply missing values |
| `app/cli.py` | accept only the current Context reference and report stable diagnostics | accept settings/preset side channels |

The old `presentation/layout/solver.py` and `presentation/layout/constraints.py` are
deleted after their retained behavior has moved to these owners. No forwarding wrapper
remains.

## 3. Slice I24-1 — Resource and resolution foundation

Deliver:

- package the v0.2 Layout and v0.4 Context schemas;
- immutable Python value objects for every size, distance, node, measurement, rectangle,
  decision, and manifest entry;
- Draft 2020-12 plus semantic validation for unique IDs, grid cells, overlay anchor
  scope, required overflow policy, size legality, and center-gap prohibition;
- canonical JSON hashing;
- single-base resolution with cycle detection and stable-ID override merge;
- Theme number-token resolution and literal-distance provenance;
- structural/semantic negative fixtures and focused unit tests.

Exit evidence:

- complete, relative, and override fixtures resolve deterministically;
- unknown override, kind mutation, duplicate ID, missing/wrong token, invalid cell,
  illegal anchor scope, center gap, and base cycle emit exact diagnostic IDs;
- no runtime code accepts a v0.2 profile without the common resolver.

Rollback boundary: new modules/schemas/tests only; product rendering is not switched.

## 4. Slice I24-2 — Normal-flow layout engine

Deliver:

- bottom-up intrinsic measurement admission;
- top-down row, column, grid, and flow arrangement;
- fixed/content/min/max/fit/fill/fr/minmax/aspect-ratio sizing;
- tokenized gap and padding;
- start/center/end/stretch and first/last baseline item placement;
- start/center/end/space-between/space-around/space-evenly distribution;
- safe versus strict alignment and required/optional overflow behavior;
- canonical Layout Manifest for normal flow.

Use `Decimal` at one declared context and quantize only when writing manifest/Scene
bounds. Property tests cover conservation of available space, bounds containment,
source-order stability, and viewport/content reflow.

Exit evidence: centered-title, 3:7 review, intrinsic legend, baseline footer, grid, and
wrapped flow tests pass twice with byte-identical manifests.

Rollback boundary: I24-1 resources remain valid even if engine changes are reverted.

## 5. Slice I24-3 — Bounded relative placement

Deliver:

- overlay normal placement;
- logical start/center/end/rational guides;
- content-derived start/end barriers;
- node/guide/barrier/parent anchors;
- stable topological ordering and cycle/scope/reference diagnostics;
- relative-decision provenance in the manifest.

Exit evidence:

- a note remains centered on a changing target;
- an anchored panel follows the widest barrier member;
- unknown/cross-scope/cyclic/center-gap cases fail before Scene;
- no public x/y offset or arbitrary equation path exists.

Rollback boundary: normal-flow I24-2 remains complete; product is still unswitched.

## 6. Slice I24-4 — Product-path replacement

This is one atomic release slice to prevent a dual-authority published state.

Deliver:

- v0.4 Render Context closure with separate Theme and Layout references;
- reusable spacing tokens in Theme fixtures;
- measured presentation sources passed once to the new engine;
- Scene construction from resolved Layout Manifest slots;
- one measure/compose adapter per source, with source-internal quantities resolved from
  closed Theme metric bindings and no renderer default table;
- CLI removal of `--presentation-settings` and any Preset/settings fallback;
- delete Presentation Preset/Settings layout resolution, v0.1 Layout schema/runtime,
  named canvas/margin/density lookup, insertion-index allocation, and obsolete tests;
- rewrite Controller Z and ASTER authoring trees to `themes/`, `layouts/`, `views/`,
  optional detail/summary files, and generated v0.4 Contexts;
- update guides, README, package resources, and dependency rules.

Exit evidence:

- repository search finds no reachable v0.1 Layout, Presentation Preset, Settings layout,
  `surface`, named header/footer sizing, `repr` manifest hash, or numeric routine spacing;
- CLI renders representative review/detail examples only through v0.4 Context;
- same Project/View with two Layouts changes geometry but not selected facts;
- same Layout with viewport/text changes reflows without YAML edits.

Rollback boundary: the entire switch is one commit. Partial old/new reachability is not
published.

## 7. Slice I24-5 — Conformance and release

Deliver:

- add the v0.2/v0.4 structural and semantic suites to the common conformance runner;
- manifest golden/property tests and deterministic SVG evidence;
- accessibility/source-metadata checks after reflow and optional omission;
- human/AI common-path validation;
- repository/package/wheel smoke tests;
- final visual acceptance and reuse review;
- close M24 ledger/roadmap status and archive the completed plans/review evidence as
  appropriate.

Exit evidence:

- full retained test and conformance suites pass;
- replacement examples render with zero required overflow;
- canonical manifests and SVG are repeatable;
- final review confirms no duplicate layout authority or compatibility shim;
- the implementation and review commits are published to `main` without force.

## 8. Traceability matrix

| Specification 33 section | Implementation slice |
|---|---|
| §2 reuse/override | I24-1 |
| §3 composition | I24-1, I24-2 |
| §4 logical axes/baselines | I24-2 |
| §5 size/distance | I24-1, I24-2 |
| §6 placement/overflow/distribution | I24-2 |
| §7 anchors/guides/barriers | I24-3 |
| §8 deterministic resolution | I24-1–I24-3 |
| §9 diagnostics | I24-1–I24-3 |
| §10 manifest | I24-2, I24-3 |
| §11 replacement/deletion | I24-4 |
| §12 acceptance invariants | I24-5 |

## 9. Stop conditions

Stop implementation and amend/publish design before continuing if any of the following
is required:

- a new source kind, data-selection operator, writing-mode rule, or size algebra;
- arbitrary constraint priorities/equations or raw coordinate authority;
- a second persisted resolved-settings contract;
- renderer-specific recovery or undeclared host measurement;
- retention of an old path for compatibility rather than a retained product semantic.

# M24 Intent-Oriented Layout Final Acceptance Review — 2026-09-21

**Decision:** PASS — M24 is complete.

## Reviewed implementation

- I24-1 profile resolution, deterministic token handling, immutable stable-ID overrides,
  and diagnostic closure;
- I24-2 normal-flow layout and canonical Layout Manifest;
- I24-3 guide, barrier, and bounded relative placement;
- I24-4 product-path replacement in commit `7e81ce1`;
- I24-5 regression, conformance, package, and publication evidence.

## Acceptance evidence

The verified local tree is exactly the tree published by `7e81ce1`:

- parent: `bf37c7a`;
- tree: `f2959f536159e920cf0f2431f42dc4dfba5bebe0`;
- `PYTHONPATH=src python -m pytest -q`: **160 passed**;
- `PYTHONPATH=src python conformance/run_conformance.py`: **Chrona conformance: PASS**,
  including presentation, traceability, AI proposal, package, profile, review-detail,
  DateTime, successor-release, and release-acceptance checks.

The product switch removes the v0.1 Layout schema/runtime, Presentation
Settings/Presentation Preset schemas and resolver, old CLI setting argument, legacy
layout tests and fixtures, and renderer-owned layout fallback. The replacement accepts
only a v0.4 Render Context with independent Theme and Layout references. Source adapters
measure once and compose only inside the resolved manifest slot; renderers serialize the
completed Scene and do not read Layout resources.

## Invariant review

| Invariant | Evidence | Result |
|---|---|---|
| Layout does not select facts | Context and View resources stay separate from Layout; source fixtures retain selected-object assertions. | Pass |
| Layout changes geometry, not facts | intent resolver and source-adapter unit tests exercise the same source set through different manifests. | Pass |
| Reflow is input-driven | intent engine fixtures vary viewport and measurements without profile edits. | Pass |
| No compatibility authority | product imports, CLI parameters, schemas, runtime resources, and authoring examples remove Settings/Preset/v0.1 Layout reachability. | Pass |
| Required/optional content is explicit | source adapter tests cover required overflow and optional omission before Scene serialization. | Pass |
| Determinism | canonical manifest, fixed metrics, SVG, and common conformance paths are repeatably asserted. | Pass |

## Publication and reuse review

The GitHub `main` update was a non-force, single-commit tree update from the verified
parent. No old/new public dual-authority state was published. Controller Z and ASTER
authoring resources use separate `themes/`, `layouts/`, `views/`, optional profiles, and
generated v0.4 Contexts. No further M24 work is open.

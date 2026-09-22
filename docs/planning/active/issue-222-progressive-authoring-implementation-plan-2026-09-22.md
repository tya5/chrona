# Issue 222 Progressive Authoring Implementation Plan

**Design authority:** [51 Progressive Authoring](../../specification/51-progressive-authoring.md) and
`docs/reviews/current/issue-222-progressive-authoring-architecture-review-2026-09-22.md`.

## Purpose

Implement the guided authoring facade without adding a second semantic, layout, Scene,
or renderer path. Every guided render must enter the existing typed `RenderClosure`
and the ordinary review use case. This plan deliberately does not add compatibility
syntax or a GUI.

## Slices

| Slice | Scope | Primary files | Acceptance / publication gate |
| --- | --- | --- | --- |
| I222-1 | Closed source contracts and preset normalization | new workspace/preset/binding schemas; schema inventory; `presentation/contracts`, `presentation/model/authoring`; unit schema and normalization tests | malformed/unknown/illegal override diagnostics; normalized contracts are existing typed resource shapes; PR merged before any CLI surface |
| I222-2 | Guided Draft render and provenance | authoring closure resolver; `render_review` ingress; CLI `render-workspace`; compact fixture and output tests | task/date/Actual/preset/scheme-only source renders through normal pipeline; deterministic output and guided provenance; explicit `render` remains unchanged |
| I222-3 | Guided mutations | successor command schema; workspace command executor; CLI command check/apply; command tests | only closed semantic/Stage-2 mutations; CAS/rejection leaves files unchanged; no Scene or geometry source fields |
| I222-4 | Stage-3 materialization and release gate | receipt schema; aggregate atomic writer; `materialize-presentation-preset`; examples and acceptance tests | complete explicit View/Theme/Scheme/Layout/Context + receipt, collision/stale/failed-proof rollback, byte-equivalence, explicit bypass, full CI/materializer checks |

## Boundaries and order

I222-1 owns parsing and conversion only. It cannot call the scheduler, layout, Scene,
or renderer. I222-2 owns the only guided ingress adapter and must construct an in-memory
typed closure; it cannot introduce a second render use case. I222-3 may operate only on
the workspace aggregate and its command registry. I222-4 is the sole aggregate write;
it must stage every result and commit only after validation and output equivalence.

The slices are strictly ordered. Before merging each slice, fetch `origin/main`, inspect
the exact diff and CI, run focused tests and the full suite, and publish a single
non-force PR. A discovered responsibility or model mismatch stops the relevant slice;
the design document and architecture review are corrected and merged before coding
resumes.

## Test matrix

* Schema positives and negatives: closed members, exact immutable preset reference,
  prohibited semantic/geometry overrides, compatible scheme selection, and receipt.
* Normalization: compact tasks/actuals become Project v0.5/Actual Set v0.2; preset
  defaults plus closed overrides become existing View/Theme/Scheme/Layout/Context.
* Rendering: identical inputs yield byte-identical output and provenance; absent,
  untrusted, or incompatible preset yields stable diagnostics; existing explicit and
  loose-resource Draft routes are unchanged.
* Mutation/materialization: base-revision conflict, collision, incomplete closure,
  failed proof, and invalid command write nothing; accepted materialization produces
  a reviewable canonical bundle and Stage-3 takes the explicit route.
* Gates: focused tests per slice, full `pytest`, `conformance/run_conformance.py`,
  public materializer checks, and generated SVG diff review in I222-4.

## Non-goals

No GUI, external synchronization, code plugins, implicit package upgrades, reverse
materialization, legacy compact parser, Scene-coordinate persistence, or renderer-local
fallback is authorized by this plan.

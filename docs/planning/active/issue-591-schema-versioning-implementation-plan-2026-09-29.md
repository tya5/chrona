# Issue #591 — schema versioning implementation plan

Public base: #591 design and whole-architecture review in [`83724e2b`](https://github.com/tya5/chrona/commit/83724e2b45242f26c7c1d21875f9c5d98806587e). Predecessor: [design record](issue-591-schema-versioning-design-plan-2026-09-29.md). This plan changes no runtime schema or resource. Normative guidance in Specs 56/05/34 and `AGENTS.md` was published with the design; the remaining implementation is a conformance guard and merge proof.

## Literal acceptance and evidence

| Issue criterion (verbatim) | Gate |
| --- | --- |
| Spec 34 and `AGENTS.md` state the additive-in-place rule for View, Layout Profile and Project schemas, consistent with Theme. | Review published Spec 34 cross-reference, `AGENTS.md`, Spec 56 normative rule, and Theme omission precedent. |
| Two parallel additive View changes merge without either bumping the version. | Two branches from one View v0.28 base, distinct optional properties, real Git merge in both orders, schema validation of old and combined resources; record commits and commands. |
| A conformance check fails a version bump whose only change is additive optional properties. | Synthetic predecessor/successor fixtures fail for one and multiple optional insertions; incompatible examples remain permitted or fail closed for a specific ambiguity; exercise registered conformance command. |

## Slices

| Slice and publication | Owned files / behavior | Focused and public gates |
| --- | --- | --- |
| I591-1 structural guard PR | `tools/schema_inventory.py`, `tests/unit/tools/test_schema_inventory.py`, `conformance/run_conformance.py` only if explicit registration is needed. Compare View/Layout Profile/Project inventory successor pairs after normalizing `$id`, versioned title, and version const. Reject only an entire additive-optional diff; fail closed on ambiguous composition/conditional optionality. Do not rewrite schemas, defaults, or old resources. | Synthetic nested/multiple additions, required addition, removal, retype, existing default/constraint change, composition ambiguity; current inventory remains valid. Run focused pytest and conformance inventory gate. Public materializer bytes must remain unchanged; CI supplies full matrix. Publish and verify exact main. |
| I591-2 independent View merge proof | Two temporary test PRs/branches, each adding a distinct optional View v0.28 field with omission-preserving consumer behavior; temporary integration branches for both merge orders. Test resources live only in proof branches unless they are a separately approved feature. | Real Git merges show no conflict, both merged schemas remain v0.28 and accept old/both-field fixtures; focused consumer tests establish omission behavior. Report branch/PR URLs and exact commands. No synthetic proof branch is merged into product `main`. |
| A591 acceptance and archive | `docs/reviews/current/` literal acceptance review, then archive only after exact review-bearing `main` CI and issue closure. | Three rows with direct links, conformance/full-main CI, generated evidence diff, architecture check. Any deferred criterion keeps #591 open. |

The guard compares inventory-declared transitions, not arbitrary historical file pairs. A schema-only check cannot prove runtime omission behavior; feature PRs must test that separately in their owning layer. No compatibility parser, automatic schema migration, or Theme checker expansion is in scope. If an existing transition exposes a comparison ambiguity or classification conflict, return to design before weakening the guard.

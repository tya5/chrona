<!-- chrona:literal-acceptance/v1 -->

# Issue #591 — schema versioning acceptance review

Source: [Issue #591](https://github.com/tya5/chrona/issues/591), observed 2026-09-30. Design/architecture and normative rule: [work record](../planning/issue-591-schema-versioning-design-plan-2026-09-29.md), [Spec 56 §3.2](../../specification/56-schema-authoring-and-diagnostics.md#32-schema-version-evolution-591). Implementation plan: [#591 plan](../planning/issue-591-schema-versioning-implementation-plan-2026-09-29.md). Product guard: [PR #607](https://github.com/tya5/chrona/pull/607), merged as [`dd393d11`](https://github.com/tya5/chrona/commit/dd393d119dfe59c516efda01f51b8bf7df3b1b9f), with [PR CI](https://github.com/tya5/chrona/actions/runs/36584657605) green.

## Literal issue acceptance

### Issue #591

- Source: [Issue #591](https://github.com/tya5/chrona/issues/591)
- Observed: 2026-09-30

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Spec 34 and `AGENTS.md` state the additive-in-place rule for View, Layout Profile and Project schemas, consistent with Theme. | met | [Spec 34](../../specification/34-color-scheme-authoring.md), [AGENTS.md](../../../AGENTS.md), normative Spec 56 §3.2 and [Theme optional-field precedent](https://github.com/tya5/chrona/commit/17e5e1a24766ecb520ea252ecf5b3ebe393f0c02). | — |
| 2 | Two parallel additive View changes merge without either bumping the version. | met | Proof-only [PR A #610](https://github.com/tya5/chrona/pull/610) and [PR B #612](https://github.com/tya5/chrona/pull/612) start at the same `dd393d11` View v0.28. Public merge orders [A→B `a7e71bb7`](https://github.com/tya5/chrona/commit/a7e71bb71da4bceacdde5da319a147dcc3daf8a3) and [B→A `f061f778`](https://github.com/tya5/chrona/commit/f061f778c9655b60706dcae5554ebede4496a0b3) had no conflict and have identical schema SHA-256 `592160af2db3a2cf122b6922eac946c4124a0a69d835556cf47a0b3cb515e426`. Both retain v0.28; the original and both-field resource validate with `jsonschema.Draft202012Validator` against each merged schema. These are demonstration branches, not product additions. | — |
| 3 | A conformance check fails a version bump whose only change is additive optional properties. | met | `tools/schema_inventory.py` registered in `conformance/run_conformance.py`; [synthetic inventory tests](../../../tests/unit/tools/test_schema_inventory.py) reject nested/multiple optional-only bumps and accept genuine incompatible changes. Focused 13 schema tests and the current historical inventory pass. | — |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Schema structure and prospective version guard remain in conformance; View/Layout Profile/Project consumers still own omission behavior, and adapters are untouched. The historical Project v0.6→v0.7 transition is intentionally outside this new authoring gate; Spec 56 and the design correction document that adoption boundary. No packaged resource, public Scene/SVG, or migration changed. The proof PRs were closed without merging into `main`. Exact review-bearing-main three-OS CI and newest-Python materializer run must pass before closing #591; record that run in the issue closing comment.

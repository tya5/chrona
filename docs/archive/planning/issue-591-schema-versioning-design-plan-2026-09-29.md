# Issue #591 — schema versioning design and review

## Published baseline and literal acceptance

Public base: [`76f3664eb0cde484e60f5c764eaf7415c0c0e790`](https://github.com/tya5/chrona/commit/76f3664eb0cde484e60f5c764eaf7415c0c0e790), fetched from `origin/main` on 2026-09-29. [Issue #591](https://github.com/tya5/chrona/issues/591) is open. The issue author’s comments identify the Spec 34 mismatch; no maintainer reply is present. Related issues #582–#588 remain the stated source of near-term additive changes; #582 adds a Project fact, named periods.

Current live schemas are View `chrona/view/v0.28`, Layout Profile `chrona/layout-profile/v0.9`, Project `timeline/v0.7`, and Theme `chrona/theme/v0.13`. Lifecycle pairs are declared in `schemas/schema-inventory-v0.1.yaml`. Runtime ingress is owned by `src/chrona/presentation/contracts/resources.py` for presentation resources and `src/chrona/core/validation.py` for Project; Layout Profile interpretation is in `src/chrona/presentation/layout/profile.py`. Conformance runs through `conformance/run_conformance.py`; existing schema patterns are in `tools/schema_inventory.py`, `tests/unit/tools/test_schema_inventory.py`, `tests/integration/test_view_v01_schema.py`, and `tests/integration/test_packaged_resources.py`.

Theme provides a concrete additive-in-place precedent: commit [`17e5e1a24766ecb520ea252ecf5b3ebe393f0c02`](https://github.com/tya5/chrona/commit/17e5e1a24766ecb520ea252ecf5b3ebe393f0c02) added optional `chipPadding` to Theme v0.11 without bumping the Theme version. `src/chrona/presentation/model/theme_tokens.py` returns zero padding when it is absent, preserving old behavior; a JSON Schema `default` annotation alone would not do this. Theme v0.11 is now transitioning to v0.13, so this is historical precedent rather than the current live version.

View version pressure is verified: v0.27 was introduced by [`ba8d99d0eeb3fa80dcdff6040fa44571016dd778`](https://github.com/tya5/chrona/commit/ba8d99d0eeb3fa80dcdff6040fa44571016dd778), and v0.28 by [`a6cf34d967c1e6f514274d8210e70967b3618698`](https://github.com/tya5/chrona/commit/a6cf34d967c1e6f514274d8210e70967b3618698), both on 2026-09-27. These lane changes may be incompatible and do not by themselves show an unnecessary bump. The checker must preserve legitimate bumps: inventory history also records incompatible migrations, such as Project v0.6→v0.7 and Layout Profile successor contracts.

Literal issue acceptance (copied verbatim):

- [ ] Spec 34 and `AGENTS.md` state the additive-in-place rule for View, Layout Profile and Project schemas, consistent with Theme.
- [ ] Two parallel additive View changes merge without either bumping the version.
- [ ] A conformance check fails a version bump whose only change is additive optional properties.

## Selected design

Normative version-evolution rules belong in Spec 56 §3.2. Spec 05 will point Project authors to that rule. To satisfy the issue’s literal “Spec 34” criterion without making Color Scheme Authoring own general schema policy, Spec 34 will receive one sentence stating the additive-in-place rule and linking to Spec 56. `AGENTS.md` will direct contributors to Spec 56 §3.2.

For View, Layout Profile, and Project, a new optional property is added to the current schema version without a version bump only when omission preserves the prior behavior. Runtime default behavior belongs to the resource consumer; JSON Schema’s `default` keyword is annotation only. A bump is reserved for incompatible changes, including removal, rename, retype, changed existing default behavior, a new required field, or another change that invalidates an existing resource or changes its behavior. Batch pending incompatible changes into the bump. The existing unsupported-version diagnostic and no-silent-upgrade rule remain in force. Theme remains the precedent and is not a new checker target.

The checker will use explicit predecessor/successor relationships in the schema inventory for View, Layout Profile, and Project, applying the guard to transitions introduced after the published View v0.28, Layout Profile v0.9, and Project v0.7 adoption baseline. Historical transitions remain untouched; Project v0.6→v0.7 already contains optional additions, so retroactive enforcement would break current conformance. Normalize only version identity metadata (`$id`, versioned title, version const, and matching root `examples[*].version` values). A new transition is an additive-only bump when its entire remaining structural diff consists of one or more new optional properties under object `properties` maps. The containing `required` declarations and all existing schema nodes must be unchanged. Any removal, existing-node change, `required` change, constraint/type/default change, or changed composition makes the transition incompatible or outside this rule. When `$ref`, `allOf`, conditionals, or other structure prevents an unambiguous optionality result, the checker fails closed with a path-specific unsupported comparison; it does not infer compatibility.

This structural check does not prove omission behavior. Focused consumer tests must show that an old resource omitting each added property retains its former runtime behavior. The parallel View proof will use two temporary branches from the same committed `view-v0.28.schema.yaml`, each adding a distinct optional property at a separate schema location without changing the version. A real Git merge must be conflict-free; the merged schema must retain v0.28, accept a resource containing both additions, and continue accepting the pre-change resource with neither. This proves merge composition and schema acceptance; consumer-level omission tests separately prove behavior.

## Whole-architecture review

The rule preserves ownership: schemas define accepted structure; the View and Layout Profile presentation contracts own their inputs; Core owns Project validation and defaults; consumers implement defaults in their layer. Conformance compares declarative schema resources and does not add runtime fallback or compatibility parsing. Adapters remain uninvolved.

Schema version remains part of the resource contract and immutable closure identity. In-place additions preserve old resources that omit the field; resources that use the new optional property use the same version. Incompatible changes retain explicit version transitions and existing unsupported-version diagnostics. Existing public resources, preset mirrors, and generated outputs require no migration for a property unused by them; changed consumer behavior would require the usual focused tests and public materializer review.

The principal checker risk is classifying composition or conditional requirements incorrectly. The selected fail-closed rule narrows false acceptance; tests must also prove that genuine incompatibilities are not blocked. Another limitation is that a schema-only diff cannot detect an unreviewed runtime default change, so the omission-behavior tests and layer review remain required. No conflict was found with Specs 05, 34, or 56 once the cross-reference ownership above is applied, or with Spec 56 §3.1’s unsupported-version and no-silent-upgrade contract.

Correction before code: the first inventory audit found Project v0.6→v0.7 has only optional property additions apart from version identity, and Layout Profile embeds its version in root schema examples. Retroactively rejecting the Project transition would break current conformance; ignoring the example version would miss a genuine future Layout Profile additive-only bump. The normative rule therefore applies prospectively after the three published live-version baselines and normalizes only matching root example version values. This changes neither runtime validation nor historical resources, preserves the existing unsupported-version contract, and keeps the guard focused on future authoring decisions.

## Draft normative changes in this worktree

- `docs/specification/56-schema-authoring-and-diagnostics.md` §3.2 states the additive/incompatible rule, default ownership, inventory-pair comparison, and fail-closed structural checker boundary.
- `docs/specification/05-project-format.md` points Project schema evolution to Spec 56 §3.2 while leaving calendar reproducibility deferrals intact.
- `docs/specification/34-color-scheme-authoring.md` has one cross-reference sentence containing the literal additive rule; it assigns no additional versioning ownership to the Color Scheme specification.
- `AGENTS.md` tells contributors to apply Spec 56 §3.2 and clarifies that schema annotations do not implement runtime defaults.

These are review drafts only. No product code, schema resource, conformance checker, or issue comment is changed by this slice.

## Evidence and next slices

| Slice | Evidence needed |
| --- | --- |
| D2 — this design/review | Spec 34 mismatch recorded; Theme optional-field history and runtime fallback verified; version owners, inventory transition pairs, unsupported-version contract, layer ownership, and checker limits reviewed |
| P1 — implementation plan | Map each literal criterion to files, tests, synthetic fixtures, parallel-merge procedure, resource/materializer checks, and publication boundary |
| I1 — guidance and normative publication | Spec 56 §3.2, Spec 05 Project pointer, Spec 34 cross-reference, and `AGENTS.md` published together after review |
| I2 — conformance and evidence | Additive-only transition rejected; required/removal/retype/default/composition cases classified correctly or fail closed; two independent View branches merge on v0.28; omission behavior remains unchanged |
| A1 — acceptance | Review has a disposition and direct evidence for all three literal criteria; exact-main CI is green before issue closure |

Predecessor: [Issue #591](https://github.com/tya5/chrona/issues/591) and the baseline plan published in this record. Successors: [implementation plan](issue-591-schema-versioning-implementation-plan-2026-09-29.md) and [acceptance review](../reviews/issue-591-schema-versioning-acceptance-review-2026-09-30.md).

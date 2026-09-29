# Issue #591 — schema versioning design plan

## Published baseline

Public base: [`a7358bcb72ad72a96cc600f09f3e5cb8dcf22981`](https://github.com/tya5/chrona/commit/a7358bcb72ad72a96cc600f09f3e5cb8dcf22981), fetched from `origin/main` on 2026-09-29. [Issue #591](https://github.com/tya5/chrona/issues/591) is open and has no comments. It reports frequent View version bumps and migration of each View file, preset, and mirror; it proposes in-place additive optional fields with behavior-preserving defaults, with bumps for incompatible changes. Its evidence for the premise (“Theme already” uses this policy) remains to be verified against current history and behavior.

The current live schema contracts are View `chrona/view/v0.28`, Layout Profile `chrona/layout-profile/v0.9`, Project `timeline/v0.7`, and Theme `chrona/theme/v0.13`. The schema lifecycle is recorded in `schemas/schema-inventory-v0.1.yaml`; View, Layout Profile, and Project have a prior transitioning schema and a live successor. Runtime/schema ownership is distributed across `src/chrona/presentation/contracts/resources.py`, `src/chrona/presentation/layout/profile.py`, and `src/chrona/core/validation.py`. `tools/schema_inventory.py` validates lifecycle metadata, and `conformance/run_conformance.py` registers that check. Existing schema tests include `tests/integration/test_view_v01_schema.py`, `tests/unit/tools/test_schema_inventory.py`, and `tests/integration/test_packaged_resources.py`.

The issue names “Spec 34” as the versioning authority. On this public base, `docs/specification/34-color-scheme-authoring.md` owns Color Scheme authoring and does not state general schema-versioning rules. `docs/specification/56-schema-authoring-and-diagnostics.md` §3.1 defines unsupported presentation-version diagnostics and says stale versions are not silently upgraded; it does not define additive schema evolution. `docs/specification/05-project-format.md` says Project versioning rules are deferred. This mismatch is unresolved; no specification target is selected by this plan.

Related open issues #582–#588 describe mostly additive presentation changes. In particular, #582 proposes a new Project fact (named periods); the remaining issues describe View, Theme, Layout Profile, or presentation behavior. Their exact dependencies and sequencing with #591 remain unverified. The current open PR list contains #424 (README), with no apparent #591 implementation dependency.

## Literal acceptance criteria

Copied verbatim from issue #591:

- [ ] Spec 34 and `AGENTS.md` state the additive-in-place rule for View, Layout Profile and Project schemas, consistent with Theme.
- [ ] Two parallel additive View changes merge without either bumping the version.
- [ ] A conformance check fails a version bump whose only change is additive optional properties.

## Design questions and boundaries

1. Resolve the “Spec 34” mismatch: confirm whether the issue intends to amend the existing Color Scheme specification, another existing specification, or a new versioning specification; also determine how the Project-format deferral should be reconciled. Keep the literal criterion visible until its disposition is agreed.
2. Establish the current Theme behavior and historical schema evolution from published commits. Distinguish the schema’s `default` annotation from runtime behavior: JSON Schema does not apply defaults, so “reproduces today’s behaviour” needs observable evidence.
3. Define what counts as an additive optional-property change, including nested properties under closed objects, and what evidence distinguishes it from a changed default, required-field addition, removal, rename, or retype. This plan selects no compatibility algorithm.
4. Identify the correct comparison inputs for conformance from the current schema inventory and version history. Decide whether the rule applies only to View, Layout Profile, and Project as written, or has any broader scope; do not silently generalize it to every schema kind.
5. Specify evidence for the parallel-change criterion: establish how two independently authored optional View changes can be composed against one live version and what merge/version evidence is required. No concurrent branch or PR is created at this planning stage.
6. Review implications for resource identity, unsupported-version diagnostics, schema inventory lifecycle, runtime defaults, public View/Project resources, preset mirrors, and the no-silent-upgrade policy before defining behavior.

Domain boundaries to preserve during design: schema files declare accepted structure; the View, Layout Profile, and Project owners define their inputs; Core and presentation consumers supply behavior; adapters do not interpret source schemas. The exact locations of defaults and any conformance ownership remain open pending design review.

## Design slices and required evidence

| Slice | Reviewable result | Evidence needed |
| --- | --- | --- |
| D1 — baseline and questions (this record) | Published issue criteria, current-main facts, unresolved Spec 34 target and design questions | Issue/comments, current schemas and inventory, owner/runtime references, existing tests and conformance registration |
| D2 — design and architecture review | Agreed versioning semantics, comparison scope, default semantics, conformance contract, migration/compatibility effects, and normative-document target | Consistency review against Specs 05, 34, 56, `AGENTS.md`, schema inventory, unsupported-version diagnostics, current Theme behavior, and related issues #582–#588 |
| P1 — implementation plan | Ordered slices with owned files, fixture strategy, focused tests, public resources/materializers, and publication boundaries | Each literal criterion mapped to direct evidence; design review complete before product changes |
| I1 — normative and contributor guidance | Approved rule published in the selected specification location and `AGENTS.md` | Exact text reviewed against selected compatibility semantics and issue’s first criterion |
| I2 — conformance and parallel-change evidence | Approved checker and synthetic evidence for additive/incompatible cases and composed independent View additions | Checker rejects an additive-only version bump; accepts representative incompatible changes; two optional View additions coexist on one version without a bump |
| A1 — acceptance review | One row for each literal criterion, issue disposition, exact commit and CI evidence | Repository acceptance gate, focused checks and required exact-main CI; issue remains open for any deferred or unverified row |

## Dependencies and next publishable step

No product-code dependency is established yet. Before D2, verify the Theme history and runtime default behavior, inspect the relevant issue histories #582–#588 for committed sequencing or shared contract decisions, and settle the specification-target ambiguity. The next independently publishable slice is this design-plan record. The next product-independent design slice is D2; implementation planning and product edits wait for its review.

## Predecessor and successor records

- Predecessor: [Issue #591](https://github.com/tya5/chrona/issues/591).
- Successor: design and architecture review to be linked here after D2 is completed; no successor document exists yet.

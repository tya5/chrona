# Design — Content identity is required by default on the Store read path (#723)

**Plan:** [implementation plan](../planning/active/issue-723-content-identity-required-by-default-implementation-plan-2026-10-01.md).
**Found by:** [#710 design](issue-710-store-address-containment-design-2026-10-01.md), part A (the `contentIdentity` finding).
Baseline: `main` at `55087f1d` (2026-10-01). Every claim marked *measured* was run at that commit with the defaults flipped in a scratch copy of the tree; nothing measured is committed except through the tests this design asks for.

## Decision being implemented

The owner (the only user of the project; there are no external Stores) authorised making verification required by default on 2026-10-01. `optional` stays available, but only as an explicit opt-out. The motivation is #710: an optional pin is not a limiter, because a reference that omits `contentIdentity` is read without any byte check.

## What exists today

`contentIdentity` is an optional exact-byte pin on a resource reference ([Spec 42](../specification/42-optional-content-identity-integrity.md), ADR-0024, Issue #44). The modes:

| Where | Today | Meaning |
|---|---|---|
| `LocalSnapshotReader(require_content_identity=False)` default | optional | a supplied pin must match (`E_CONTENT_IDENTITY`); an omitted pin is accepted and the reader computes the identity |
| `LocalSnapshotReader(require_content_identity=True)` | required | an omitted pin raises `E_CONTENT_IDENTITY_REQUIRED` |
| `LocalBaselineRegistry(require_content_identity=False)` default | optional | same, but the read is always also pinned by `revision.token == baseline:<sha256>`, so a baseline read is never unpinned in effect |
| Store config `integrity: optional \| required`; omitted means `optional` (`ConfiguredStoreReader`) | per Store | `required` rejects an omitted pin before the read; `optional` builds `LocalSnapshotReader` with its default |
| CLI `--require-content-identity` (`validate`, `schedule`, `review`, `render-review`, `render-review-gallery`) | opt-in strict | maps to the reader flag |
| `chrona init --example` | writes `integrity: optional` | |
| Extension packages | always require a pin (Spec 42 "Mandatory pins") | unchanged |

## Every site found (grep for `integrity`, `require_content_identity`, `LocalSnapshotReader(`, `ConfiguredStoreReader`, `contentIdentity`)

Source:

- `storage/revision_store.py` `LocalSnapshotReader.__init__` (default) and `.read` (the check).
- `storage/snapshots.py` `LocalBaselineRegistry.__init__` (default) and `.read`.
- `operational/store_config.py`: `entry.get("integrity", "optional")`, and `LocalSnapshotReader(root, key[1])` built without the flag.
- `usecases/local_authoring.py` `initialize_project`: writes `"integrity": "optional"`.
- `app/cli.py`: the flag on five sub-commands and four `LocalSnapshotReader(...)` constructions; `_store_reader` builds the configured reader for `command apply` and `undo`.
- `schemas/store-config-v0.1.schema.yaml`: `integrity` is an enum `[optional, required]` with no default. It is not edited here (the #710 schema half owns `schemas/`); the default is behaviour, not schema.

Not readers of the Store: `tools/materialize_example.py` `_verify_identity` and `usecases/materialize.py` verify a supplied pin on bytes they copy and stage through their own overlay reader. The public materializer is therefore unaffected by the flip (*measured*: `tools/regenerate_public_examples.py --check` passes, 29 slides, and `conformance/run_conformance.py` passes, with the defaults flipped).

Spec and docs: Spec 42 (policy text), Spec 54 and ADR-0030 (the materializer does not invoke strict mode), `docs/guides/cli-reference.md` (generated from argparse), README (the `render-review` and `schedule` examples are `doc-check skip`, author-created references).

## What flips

1. `LocalSnapshotReader` and `LocalBaselineRegistry` default to `require_content_identity=True`.
2. A Store config that omits `integrity` means `required`. `ConfiguredStoreReader` passes the flag to the readers explicitly from the entry's value (`optional` becomes an explicit `require_content_identity=False`).
3. `chrona init --example` writes `integrity: required`.
4. The CLI inverts: `--require-content-identity` is replaced by `--allow-missing-content-identity` (explicit opt-out; there is no outside caller to keep a deprecated alias for).
5. Spec 42 is amended: the schema still permits omission; the Store read path rejects it unless the Store or the caller opts out.

Stays available as the explicit opt-out: `LocalSnapshotReader(..., require_content_identity=False)`, `integrity: optional` in a Store config, `--allow-missing-content-identity` on the CLI.

## What breaks when a reference has no `contentIdentity` (*measured*)

The change is on the **reference**, not the snapshot bytes: a reference without `contentIdentity` is refused with `E_CONTENT_IDENTITY_REQUIRED` (`SnapshotReadError`, surfaced by the closure as `ClosureError`). A mismatch still gives `E_CONTENT_IDENTITY`. Surveying committed YAML for resource references (`store` + `address` + `revision`):

| Place | Unpinned | Pinned |
|---|---|---|
| `examples/*/contexts` (halcyon-1, controller-z, controller-z-ja, aster-ssd, orion-asic) | 191 | 17 |
| `examples/halcyon-1/snapshots` | 1 | 0 |
| `conformance/**`, `docs/examples/operational-workflows`, `examples/orion-asic/project.yaml` | 0 | all |

The canonical example Contexts are unpinned **by design** (ADR-0030, Spec 54; PR #53's full-pin conversion was not merged). This design does not change that: the Contexts stay byte-identical, the schemas keep permitting omission, and the public materializer keeps working because it stages and verifies through its own overlay reader, then renders from a closure whose Context reference is pinned. Only direct reads of an example Store through `LocalSnapshotReader` are affected.

### Blast radius with the defaults flipped (full `tests/`: 32 failed, 2686 passed, 26 skipped)

| Failure group | Count | Cause | Migration |
|---|---|---|---|
| `tests/unit/chrona/usecases/test_render_review.py` (via `_closure`, and one direct reader) | 24 | reads a copied example closure through `LocalSnapshotReader` | state `require_content_identity=False` with the reason (canonical examples are unpinned, ADR-0030) |
| `tests/integration/test_materialize_example.py` | 5 | same, five reader constructions | same |
| `tests/integration/test_issue_478_role_admission.py` | 1 | same | same |
| `tests/unit/chrona/storage/test_revision_store_identity.py` | 1 | asserted the optional default | rewritten: default refuses, `False` is the opt-out |
| `tests/unit/chrona/test_store_address_containment.py` | 2 | legitimate-address reads use unpinned references | give the references their computed identity (the test is about containment, not identity) |
| `tests/unit/chrona/usecases/test_local_authoring.py` | 1 | resolves every halcyon Context closure through the init'd `required` Store config | see Risks |
| `tests/cli/test_cli.py::test_cli_gallery_rejects_duplicate_scheme_before_rendering` | 1 | hand-built `Namespace(require_content_identity=...)` | rename the attribute |

No migration weakens a test: each either gains the identity or names the opt-out and the reason.

## Risks, stated honestly

1. **The init'd example Store cannot resolve its own unpinned Contexts through its own config.** `chrona init --example` copies unpinned canonical Contexts into `.chrona/store`, and now writes `integrity: required`. No CLI path resolves a Context through `ConfiguredStoreReader` (`_store_reader` serves `command apply` and `undo`, which read the project reference a command names), so no shipped command breaks. Only `test_explicit_halcyon_init_is_store_resolvable_without_root_revision_closures` did, and it builds a reader from the config's root with the opt-out stated. The alternative, pinning the 191 example references, was rejected here: it reverses ADR-0030 and rewrites every canonical Context. If the owner wants that, it is a separate issue.
2. **Authors with unpinned Contexts must opt out or pin.** `chrona render-review --context-reference X --snapshot-root S` on an unpinned Context now fails with `E_CONTENT_IDENTITY_REQUIRED`. The owner is the only user; the code names the cause and `--allow-missing-content-identity` is the documented escape.
3. **ADR-0030 and Spec 42/54 wording** calls optional pins the ordinary contract. Spec 42 is amended; ADR-0030's decision (the materializer does not require pins) still holds and is recorded as unaffected, not reversed.
4. **Windows.** All new tests decide from reference data and reader flags, not the host OS. The three-OS run on `main` follows merge.
5. **The schema half of #710 is concurrent.** `schemas/` and `core/store_address.py` are not touched here.

## Verification

- A mismatch gives `E_CONTENT_IDENTITY` and a missing identity gives `E_CONTENT_IDENTITY_REQUIRED` with every default left alone, on `LocalSnapshotReader`, `LocalBaselineRegistry` and `ConfiguredStoreReader` (omitted `integrity`).
- `optional` is an explicit opt-out in all three; `initialize_project` writes `required`.
- Mutation check: flipping the `LocalSnapshotReader` default back, and the config default back, each fail a named test.

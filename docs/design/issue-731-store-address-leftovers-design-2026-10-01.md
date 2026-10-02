# Design — Store address leftovers from #710 (#731)

**Plan:** [implementation plan](../archive/planning/issue-731-store-address-leftovers-implementation-plan-2026-10-01.md).
Predecessor design: [#710 design](issue-710-store-address-containment-design-2026-10-01.md) (parts C, D, E);
[#710 acceptance review](../archive/reviews/issue-710-store-address-containment-acceptance-review-2026-10-01.md).
Evolution rule: [Spec 56 §3.2 and §7](../specification/56-schema-authoring-and-diagnostics.md).

Baseline: `main` at `6c46123a` (2026-10-01). Claims marked *measured* were run against that commit with throwaway scripts that are
not committed. The project has one user and no external Stores, so compatibility with outside data is not a concern; committed and
packaged documents must keep working.

## Decisions (fixed by the lead engineer, 2026-10-01)

1. **The runtime guard refuses exactly what `storeAddress` refuses**, for Store *addresses*. Callers that need a wider character set
   (below) get an explicit mode, not a weaker address rule.
2. **Leftover schema sites use Spec 56 §3.2's in-place clause** (a refusal the consumer already makes moves earlier; no accepted valid
   document changes) instead of a version bump, but only where that premise is verified per site and per rejected input (part C).
   Project is not bumped.
3. **The five loose predecessors are removed now**, not after "one release", because with one user the only condition that matters is
   that every committed, packaged and test document is already on the successor. `snapshot-ref` v0.2 stays readable.

## A. The runtime guard against the schema (reviewer's added item)

`check_store_address` (`src/chrona/core/store_address.py`) refuses a backslash, a colon, control characters, any anchor, empty segments and
segments made only of dots and spaces. It does not restrict the character set, so it accepts what `storeAddress` refuses: spaces, non-ASCII
letters, a trailing-space segment (`a /b`), and every other character outside `[A-Za-z0-9._-]` (`+`, `@`, `%`, `~`, `#`, `;`, quotes, `*`, `?`,
`<`, `>`, `|`). *Measured* over every string of length 0 to 4 on the 13-character alphabet `a 0 . - _ / \n space : \ NUL é +` (30,941
strings): the guard accepts 4,422 that the schema refuses (every one involves a space, `é` or `+`) and refuses none that the schema accepts.
The existing test `test_the_schema_never_accepts_what_the_code_guard_refuses` proves only the other direction (the schema is at least as
strict as the guard).

### A1. Callers of the shared function (every one, measured by `grep`)

| Caller | What is joined | Where the text comes from | Mode |
| --- | --- | --- | --- |
| `storage/revision_store.py` `LocalSnapshotReader.read` | `address` of a pinned reference | document or command | address |
| `storage/snapshots.py` `read` | `address` of a `snapshot-ref` reference | document | address |
| `storage/snapshots.py` `publish` | `snapshots/<snapshotId>.yaml` | `payload.snapshotId`; the same text is emitted as the `address` of the result reference and `command-request` v0.3 declares `snapshotId` as `storeAddress` | address |
| `usecases/materialize.py` `_inside`, `_package_resource`, icon asset check | Context, catalog and icon addresses | document | address |
| `presentation/model/font_resources.py` | font locator address | document | address |
| `presentation/model/closure.py` `_safe_icon_address`, icon asset resolve | catalog `source.address` | document | address |
| `presentation/model/theme_inheritance.py` | `extends.path` | document | address |
| `presentation/model/closure.py` `_declared_child` | preset and catalog `path` of a guided workspace | document, schema `safeRelativePath` (ASCII only) | address |
| `usecases/authoring_materialization.py` `_relative`, `_child` | `directory` of the materialize command and preset paths | command and document, schema `safeRelativePath` | address |
| `operational/authoring_commands.py` `_relative` for resource names and the marker's `directory` | `<directory>/<fixed file name>` | derived from `safeRelativePath` plus a fixed name | address |
| `operational/authoring_commands.py` `_relative` for the **workspace file name** (`cas_write_authoring_aggregate`) | `path.name` of the workspace, one segment | the operator's file name; `authoring-command` v0.1 declares `target.path` as `fileName` on purpose (#693, S1d): `my plan.yaml` and `計画.yaml` work | **file-name** |
| `commands/actual_commands.py` `LocalActualStore`, `operational/command_engine.py` | `actual-tips/<actual set id>.json` | the Actual Set `id` (schema: `minLength: 1`, so spaces and non-ASCII are valid ids). An adapter-private file name, never emitted as an address | **file-name** |

The two **file-name** callers join an identifier or a file name, not an address; they must keep accepting every value they accept today.
Making them strict would silently refuse a valid workspace name or Actual Set id. The `snapshotId` is an address (it is emitted as one and
schema-checked as one), so it is strict.

### A2. The rule

`check_store_address(address, *, charset="address")`, `check_store_segment(name, *, charset="address")` and
`resolve_store_address(base, address, *, root=None, charset="address")`:

* `charset="address"` (default): in addition to today's checks, every segment matches `[A-Za-z0-9._-]+` (a full match, so no trailing newline
  gets through) and is not made only of dots. Nothing else is added or dropped: the verdict equals `storeAddress` on every string. The
  existing structural checks stay (defence in depth; they are implied by the character set and give a precise reason).
* `charset="file-name"`: exactly today's checks (one file-name segment rule: no backslash, colon, NUL or control character, no anchor,
  no empty or dots-and-spaces segment). It is used only by the two callers marked above and is not an address rule.

The decision stays pure and host independent. Tests decide from data (the `storeAddress` validator, `PurePosixPath`/`PureWindowsPath`
flavours), never from the host OS: a three-OS run follows the merge and a Windows-only failure blocks closure of the issue.

### A3. Test design

* Parity: over an exhaustive alphabet product (`a 0 . - _ / \n space : \ NUL é + ~`, length 0 to 5) `check_store_address` accepts iff the
  `storeAddress` validator accepts. This replaces the one-direction test.
* Named vectors: space, non-ASCII, trailing-space segment, `a+b`, `a%20b`, `a;b` refused; `.hidden`, `a..b`, `a./b` accepted.
* Mode: the same inputs under `charset="file-name"` still accept `my plan.yaml`, `計画.yaml` and the Actual Set id `作業 1`, while a
  backslash, colon, control character, anchor and `..` stay refused; the workspace-name call and the actual-tip call are exercised end to
  end through `cas_write_authoring_aggregate` and `LocalActualStore`.
* Mutation check of each new rule (character class, all-dot rule, mode plumbing at each of the three call sites) recorded in the PR body.
* Tests whose fixtures used a space in an address (for example `"a b/c"` in the containment accept list) move to the refused list.

## B. The three leftover schema sites: per-site verification

Probe: an input is *narrowed* when the old site accepts it and `storeAddress` refuses it, *widened* in the other direction. Verdicts are
`True` = accepted. Columns: the old site, `storeAddress`, the consumer's check **today** (the current shared guard, or the site's own
check) and the shared guard **after slice A** (it equals `storeAddress`, by the parity test).

### B1. `icon-catalog-v0.4` `rasterSource.address` (consumers: `closure.py` `_load_icon_assets`/`_load_draft_icon_assets`, `materialize.py`)

| Narrowed input | old | `storeAddress` | consumer today | consumer after A |
| --- | --- | --- | --- | --- |
| `a\n` (trailing newline; the pattern ends in `$`) | accepted | refused | refused (control character) | refused |
| `a//b` | accepted | refused | refused (empty segment) | refused |
| `a/` | accepted | refused | refused (empty segment) | refused |
| `a/...` and `a/.../b` | accepted | refused | refused (all-dot segment) | refused |

Widened (listed as a moved verdict, not a refusal): `.hidden/x`, `_x`, `-x` (the old pattern required a leading letter or digit; the guard
and `storeAddress` accept them, and they name an ordinary file inside the root).

**The premise is false for one population.** The closure checks an address only for a raster entry that the view or theme *selects*
(`_selected_catalog_entries`, then `_safe_icon_address`); `materialize.py` checks every entry. A catalog whose **unselected** raster entry
carries `a/.../b` is valid today and is never opened by the closure. Moving the site to `storeAddress` would refuse that catalog: a document
that is accepted today would change, which is not "a refusal the consumer already makes". **Stop for this site** (below).

### B2. `preset-library-v0.2` `address` (consumer: `usecases/preset_library.py` `_safe`, packaged catalogue only)

The same five narrowed inputs, same widening. Consumer today: `_safe` is **not** the shared guard. It is a `PurePosixPath` check, and it
*accepts* `a\n`, `a/...` and `a/.../b` (refuses `a//b` and `a/`, accepts `a\x00b`, `a\\b`, `a:b` that the old schema already refuses). So the
premise is false for three of the five narrowed inputs. The catalogue is shipped, so no user can supply such a value, and every committed
address passes. **Stop for this site** (below).

### B3. Project `extensions[].resource` and the loose `revision-store-resource-ref-v0.1`

The issue and `tests/unit/tools/test_store_address_retirement.py` describe this as one site; it is two:

* `extensions[].resource` of `project-v0.7` is `type: object`: **no address pattern exists** to tighten. `resolve_package_manifests` hands the
  object to the reader, which the shared guard protects. Constraining it is a Project schema change; the decision says do not bump Project.
* `profiles.py` `_validate_value` validates each `resourceReference` field value (`artifacts`, `acceptanceEvidence` of implementation-delivery
  work items) against the frozen `revision-store-resource-ref-v0.1`. Nothing in `src` ever opens such a reference afterwards
  (*measured*: `resourceReference` and the evidence field names occur only in `profiles.py`). A loose address such as `a b.yaml` or
  `a/.../b` is therefore **accepted today and never refused later**. Moving the check to `-v0.2` would newly refuse a document that is
  valid now. The premise is false. **Stop for this site** (below).

### B4. Disposition (the options below are decided in B5)

None of the three sites meets the verified premise, so slice B changes no schema, no pattern and no expected delta. What it does:

* Spec 56 §3.2 gets the sentence the decision asked for, with the condition that these three sites showed matters: the in-place reading
  holds only when the consumer refuses the value *wherever the schema would have accepted a document that carries it*, including a document
  that carries the address without opening it; otherwise the change is a narrowing to be named, or a bump.
* This note records each site, the exact inputs, and the options for the lead (each is a one-line change once chosen):
  1. B2 only: make `_safe` call `check_store_address` (the catalogue is packaged, every committed address passes), after which B2's premise
     holds and the schema moves in place. Packaged data cannot change under a user.
  2. B1, B3: either name the narrowing (the inputs above, only in addresses nobody opens), which §3.2 already allows for "an input that
     worked and is now refused" when no working input is lost, or bump `icon-catalog` and Project.
* Open question for the owner, not decided here: whether evidence references (`artifacts`, `acceptanceEvidence`) should be opened and
  verified at all (`IDP-EVIDENCE-001` in Spec 17 reads as if they were).

### B5. Lead decisions for the three sites (2026-10-01, slice I731-D)

B4's options are decided as follows. The premise of Spec 56 §3.2's in-place clause is made true by a consumer change, then the schema moves.

1. **`preset-library-v0.2` `address` moves in place.** `usecases/preset_library.py` `_safe` calls the shared guard (`check_store_address`, default `address`
   charset) and keeps `E_BUILTIN_PRESET_RESOURCE`, so the consumer refuses every value `storeAddress` refuses (including `a\n`, `a/...`, `a/.../b`,
   `a\x00b`, `a\\b`, `a:b`). The library is packaged data: every `sourceRoot`, `sourcePath` and `noticeSourcePath` of the committed
   `library.yaml` (67 values) was *measured* to pass the guard. The schema `address` then references `storeAddress` in place.
2. **`icon-catalog-v0.4` `source.address` moves in place, with a parse-time check.** `_icon_catalog_contract` (the single parse step of
   every catalog, selected entries or not) passes every declared raster `source.address` of a v0.4 catalog through the shared guard
   and refuses the catalog with `E_ICON_ASSET_PATH` at `/body/icons/<name>/source/address`. An entry that nothing selects can therefore no longer
   carry an unsafe address, which was the only population for which B1's premise failed. The schema is not consulted for unselected entries
   (the envelope validates one representative), which is why the schema alone could never have closed this. Every committed v0.4 catalog
   (the packaged Theme Asset Catalog and the test fixture; neither has a raster entry) was *measured* to pass. The Material Symbols catalog is
   v0.3 and is not touched (v0.3 keeps its own pattern). The check is O(entries) dictionary reads; the measured load-time effect is in the PR.
3. **Project evidence references are not changed.** `profiles.py` validates `resourceReference` fields (`artifacts`, `acceptanceEvidence`)
   against the loose `revision-store-resource-ref-v0.1`; nothing opens such a reference. A loose address there is accepted and never used.
   Tightening it would newly refuse a document that is valid now, so it needs a Project version bump (batched with the next incompatible
   Project change). Open question for the owner: should evidence references be opened and verified at all?
4. **Widening, recorded.** `storeAddress` accepts a leading `.`, `_` or `-`; the old patterns (`safeRelativePath`, the icon-catalog pattern)
   required a letter or digit first. These inputs (`.hidden/x`, `_x`, `-x`) become accepted by the schema. No consumer is harmed: the shared guard
   (already equal to `storeAddress`) accepts them, they name an ordinary file inside the root, and the Windows alias rule applies only to
   all-dot or dots-and-spaces segments, which both refuse. The widening is listed in the S0 expected deltas (L1 pointers and L3 probes), each
   with a test.

## C. Retiring the loose predecessors

Rule (Spec 56 §6 and the inventory): a predecessor is removed when no committed, packaged or test document names it and its parser path is
dropped. The `transitioning` inventory entry goes, its schema file moves with `git mv` to `docs/archive/schemas/`, the removal slice
(`issue-710-…-retirement`) is satisfied, and `test_store_address_retirement.py` is updated in the same PR. Edits are scripted: dry run,
counted replacements, diff summary.

Measured at `6c46123a` (occurrences of the version string; every committed Context and Layout Profile was already re-pointed to
`layout-profile` v0.10 and `render-context` v0.17 in #724):

| Predecessor | Occurrences outside the schema file | Where |
| --- | --- | --- |
| `layout-profile` v0.9 | 11 in 7 files | `LAYOUT_SCHEMAS`, the contract `_SCHEMAS` entry, the retirement test, historical `docs/` notes |
| `render-context` v0.16 | 11 in 7 files | `RENDER_CONTEXT_VERSIONS`, `_SCHEMAS`, the retirement test, `docs/` notes |
| `command-request` v0.2 (`chrona/command/v0.2`) | 21 in 14 files | `COMMAND_SCHEMAS`, tests, docs |
| `automation-result` v0.1 | 15 in 7 files | `AUTOMATION_RESULT_SCHEMAS`, writers (`cli.py`, `command_engine.py`, `baselines.py`), the stamping fallback, tests |
| `snapshot-ref` v0.2 | 13 in 10 files | `SNAPSHOT_REF_VERSIONS` (authoring side), tests |

Per predecessor the removal slice deletes: the file (archived), the inventory entry, the registration, the `docs/specification` sentence's
"stays readable" wording for it, the retirement test row, and migrates every remaining document or test to the successor. Anything that
changes a Scene byte, or that makes a committed document newly rejected, is a stop-and-report condition; derived evidence is compared before
and after (`python -m tools.derived_evidence --check`, `python -m tools.regenerate_public_examples --check`) and only provenance version
lines may differ, which CI's derived-sync regenerates.

**`snapshot-ref` v0.2 is the exception.** `examples/halcyon-1/snapshots/baseline-2027-06.yaml` is a committed v0.2 baseline, pinned by bytes
through the replan Context (`contentIdentity`); rewriting it would change its identity and the Context's. So only the *authoring* fallback
(the writer choosing v0.2 for a Project reference that still carries a legacy loose address) is removed: with the loose address gone from
every committed document the writer always emits v0.3. The v0.2 schema, its `transitioning` entry and its read registration stay, with the
removal slice renamed so it no longer promises removal of the file.

**`revision-store-resource-ref-v0.1` stays** (a frozen part): after C3 and C4 the only remaining user is `profiles.py` (B3) and the part
registration; it goes when that is decided. The loose `relativeAddress*` definitions stay frozen in `common-v0.1`; after C1 and C2 nothing
references them and they can be dropped with a new `common` part version, which is outside this issue.

## Risks and stops

* Stop condition for slices C: a Scene byte changes, or a committed or packaged document is newly rejected.
* A slice may not edit derived documents (`docs/diagnostics/inventory.md`, `declared-value-inventory.md`, `vocabulary-inventory.md`,
  `gallery/presentation-coverage.md`, `examples/*/generated/*`): `derived-preview` rejects them; CI's derived-sync regenerates them after merge.
* Shared hotspots (the schema inventory, `expected-deltas`, `resources/__init__.py`) are edited line-locally and rebased right before merge.
